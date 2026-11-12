"""Guideline health, precedent ledger and fix verification APIs."""
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import re
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select, func
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.models.entities import (
    Rule, RuleExample, Fact, ContentItem, ContentRevision, ClaimFinding,
    FindingDecision, Precedent, AuditEvent, AICall, Workspace,
)
from app.services.guideline_health import (
    conflict_rubric_prompt,
    override_rate_issue,
    rule_vector,
    rule_pair_candidates,
    vague_rule_issue,
)
from app.services.fixes import (
    ModelFixSuggestion,
    generate_minimal_fix,
    measure_intent,
)
from app.services.precedents import (
    matching_approved_precedents,
    precedent_embedding,
    precedent_suggestion,
)
from app.services.semantic_retrieval import ollama_nli
from app.services.model_provider import ModelStepFailed, configured_provider, validated_json
from app.services.text_intelligence import mask_sensitive_with_map

router = APIRouter(tags=["guideline health, precedents and verification"])
OWNER_ROLES = {"manager", "admin"}
REVIEW_ROLES = {"reviewer", "manager", "admin"}
def require_role(user, roles):
    if user.role not in roles: raise HTTPException(403, "Your workspace role does not permit this action.")

class PrecedentInput(BaseModel):
    finding_id: str
    rule_id: str | None = None
    channel: str | None = Field(default=None, max_length=40)
    pattern_text: str = Field(min_length=3, max_length=2000)
    reason: str = Field(min_length=3, max_length=3000)
    valid_to: datetime | None = None

class VerifyInput(BaseModel):
    proposed_text: str = Field(min_length=1, max_length=20000)
    finding_id: str | None = None


class GuidelineDecisionInput(BaseModel):
    issue_key: str = Field(min_length=16, max_length=64)
    rule_id: str | None = None
    issue_type: str | None = None
    action: str = Field(pattern="^(accept|edit|ignore)$")
    edited_wording: str | None = Field(default=None, max_length=4000)


class ModelModeInput(BaseModel):
    mode: str = Field(pattern="^(deterministic|disabled|ollama)$")


class VagueRuleRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    testable_condition: bool
    has_example: bool
    clearer_wording: str = Field(min_length=1, max_length=2000)


class ConflictRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contradiction: bool
    conflicting_requirements: list[str] = Field(max_length=4)
    rationale: str = Field(min_length=1, max_length=1000)


async def _workspace_settings(db, workspace_id: str) -> dict:
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    return dict(workspace.settings or {}) if workspace else {}


async def _log_model_call(
    db, workspace_id: str, provider: str, model: str, purpose: str,
    text: str, masked_count: int, status: str, duration_ms: int | None = None,
):
    call = AICall(
            workspace_id=workspace_id,
            provider=provider,
            model=model,
            purpose=purpose,
            input_chars=len(text),
            masked_entities=masked_count,
            duration_ms=duration_ms,
            status=status,
        )
    db.add(call)
    return call


async def _guideline_rubric(
    db,
    *,
    workspace_id: str,
    model_mode: str,
    secret_terms: list[str],
    purpose: str,
    system_prompt: str,
    raw_prompt: str,
    output_model: type[BaseModel],
):
    masked, masked_count, _ = mask_sensitive_with_map(raw_prompt, secret_terms)
    provider = configured_provider(settings, model_mode)
    attempt_started: dict[int, float] = {}
    attempt_calls: dict[int, AICall] = {}

    async def on_call(status: str, attempt: int):
        if status == "started":
            attempt_started[attempt] = time.perf_counter()
            attempt_calls[attempt] = await _log_model_call(
                db, workspace_id, provider.name, provider.model, purpose,
                masked, masked_count, "started",
            )
            return
        elapsed = None
        if status in {"completed", "failed"} and attempt in attempt_started:
            elapsed = round((time.perf_counter() - attempt_started.pop(attempt)) * 1000)
        call = attempt_calls.pop(attempt, None)
        if call:
            call.status = status
            call.duration_ms = elapsed

    result = await validated_json(
        provider,
        system_prompt=system_prompt,
        user_prompt=masked,
        output_model=output_model,
        on_call=on_call,
    )
    return result

@router.get('/guideline-health')
async def guideline_health(user: CurrentUser, db: DBSession):
    rules = (await db.scalars(select(Rule).where(Rule.workspace_id==user.workspace_id, Rule.status=='active'))).all()
    issues = []
    workspace_settings = await _workspace_settings(db, user.workspace_id)
    model_mode = str(workspace_settings.get("model_mode") or settings.model_mode).lower()
    secret_terms = workspace_settings.get("secret_terms", [])
    examples_by_rule = {}
    for r in rules:
        rule_vector(r)
        examples_by_rule[r.id] = (await db.scalars(
            select(RuleExample)
            .join(Rule, Rule.id == RuleExample.rule_id)
            .where(RuleExample.rule_id == r.id, Rule.workspace_id == user.workspace_id)
        )).all()
        issue = vague_rule_issue(r, examples_by_rule[r.id])
        if issue:
            if model_mode not in {"disabled", "deterministic", "off"}:
                try:
                    rubric = await _guideline_rubric(
                        db,
                        workspace_id=user.workspace_id,
                        model_mode=model_mode,
                        secret_terms=secret_terms,
                        purpose="guideline_vagueness",
                        system_prompt=(
                            "Apply the vague-rule rubric exactly. Decide whether the guideline has "
                            "a testable condition and at least one concrete example. Do not invent "
                            "policy. Suggest clearer wording without changing the rule."
                        ),
                        raw_prompt=(
                            f"RULE {r.code}: {r.title}\n{r.text}\n"
                            "EXAMPLES:\n"
                            + "\n".join(
                                f"- {example.kind}: {example.text}"
                                for example in examples_by_rule[r.id]
                            )
                        ),
                        output_model=VagueRuleRubric,
                    )
                    issue["model_rubric"] = rubric.model_dump()
                    issue["suggestion"] = rubric.clearer_wording
                    issue["testable_condition"] = rubric.testable_condition
                    issue["has_example"] = rubric.has_example
                    issue["analysis_status"] = "completed"
                    if rubric.testable_condition and rubric.has_example:
                        issue["severity"] = "review"
                        issue["explanation"] += (
                            " The model rubric found both a testable condition and an example; "
                            "owner review is still recommended."
                        )
                except Exception:
                    issue["analysis_status"] = "needs_human_review"
                    issue["explanation"] += " The model rubric failed; review this rule manually."
            issue.update({"severity": "major", "rank": 0.8})
            issues.append(issue)

    pairs = rule_pair_candidates(rules)
    for pair in pairs:
        left, right = pair["rule"], pair["other_rule"]
        candidate = {
            "type": "possible_conflict",
            "severity": "review",
            "rule_id": left.id,
            "other_rule_id": right.id,
            "code": f"{left.code} / {right.code}",
            "title": f"{left.title} ↔ {right.title}",
            "similarity": pair["similarity"],
            "explanation": (
                "Rules have similar wording or overlapping channel scope. This is a candidate, "
                "not proof of contradiction."
            ),
            "suggestion": "Clarify the channel scope and state a condition that resolves the conflict.",
            "rank": pair["similarity"],
            "analysis_status": "candidate_only",
        }
        if model_mode == "ollama":
            raw = f"{left.text}\n{right.text}"
            try:
                masked, masked_count, _ = mask_sensitive_with_map(raw, secret_terms)
                left_masked, right_masked = masked.split("\n", 1)
                forward_started = time.perf_counter()
                forward = await ollama_nli(
                    left_masked[:2000], right_masked[:3000],
                    settings.ollama_base_url, settings.ollama_model,
                )
                forward_duration = round((time.perf_counter() - forward_started) * 1000)
                reverse_started = time.perf_counter()
                reverse = await ollama_nli(
                    right_masked[:2000], left_masked[:3000],
                    settings.ollama_base_url, settings.ollama_model,
                )
                reverse_duration = round((time.perf_counter() - reverse_started) * 1000)
                for response, duration in (
                    (forward, forward_duration),
                    (reverse, reverse_duration),
                ):
                    await _log_model_call(
                        db, user.workspace_id, "ollama", settings.ollama_model,
                        "guideline_nli", masked, masked_count,
                        response.get("status", "needs_human_review"), duration,
                    )
                candidate["nli_directions"] = [forward["label"], reverse["label"]]
                candidate["analysis_status"] = (
                    "needs_human_review"
                    if "needs_human_review" in {forward.get("status"), reverse.get("status")}
                    else "completed"
                )
                if forward["label"] == "contradicted" and reverse["label"] == "contradicted":
                    candidate["severity"] = "major"
                    candidate["explanation"] = (
                        "Bidirectional local NLI found a possible contradiction; guideline owner "
                        "confirmation is required."
                    )
                    rubric = await _guideline_rubric(
                        db,
                        workspace_id=user.workspace_id,
                        model_mode=model_mode,
                        secret_terms=secret_terms,
                        purpose="guideline_conflict_rubric",
                        system_prompt=(
                            "Return a strict assessment of actual incompatibility. Both rules must "
                            "apply to overlapping content. Preserve exact rule wording and never "
                            "edit either rule."
                        ),
                        raw_prompt=conflict_rubric_prompt(left, right),
                        output_model=ConflictRubric,
                    )
                    candidate["model_rubric"] = rubric.model_dump()
                    candidate["analysis_status"] = "completed"
                    candidate["severity"] = "major" if rubric.contradiction else "review"
                    candidate["explanation"] = rubric.rationale
            except Exception:
                candidate["analysis_status"] = "needs_human_review"
                candidate["explanation"] += " Local NLI could not complete; verify both rules manually."
        issues.append(candidate)

    flags = (await db.scalars(
        select(ClaimFinding).where(ClaimFinding.workspace_id == user.workspace_id)
    )).all()
    decisions = (await db.scalars(
        select(FindingDecision).where(
            FindingDecision.workspace_id == user.workspace_id,
            FindingDecision.action == "override",
        )
    )).all()
    override_by_finding = {}
    for decision in decisions:
        override_by_finding[decision.finding_id] = (
            override_by_finding.get(decision.finding_id, 0) + 1
        )
    for rule in rules:
        related = [
            finding for finding in flags
            if any(
                evidence.get("code") == rule.code
                or evidence.get("rule_id") == rule.id
                or evidence.get("id") == rule.id
                for evidence in (finding.evidence or [])
            )
        ]
        issue = override_rate_issue(
            rule, len(related),
            sum(override_by_finding.get(finding.id, 0) for finding in related),
        )
        if issue:
            issue["severity"] = "review"
            issue["rank"] = issue["override_rate"]
            issues.append(issue)

    for issue in issues:
        identity = ":".join(
            str(issue.get(key, ""))
            for key in ("type", "rule_id", "other_rule_id", "code")
        )
        issue["issue_key"] = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    issues.sort(key=lambda issue: (-issue.get("rank", 0), issue["type"], issue.get("code", "")))
    await db.commit()
    return {
        "active_rules": len(rules),
        "issue_count": len(issues),
        "issues": issues,
        "method": "embedding_candidates_with_heuristic_screening",
        "model_mode": model_mode,
        "notice": "No rule changes are automatic. A guideline owner must accept, edit, or ignore each issue.",
    }


@router.post('/guideline-health/decisions', status_code=201)
async def decide_guideline_issue(body: GuidelineDecisionInput, user: CurrentUser, db: DBSession):
    require_role(user, OWNER_ROLES)
    if body.action == "edit" and not (body.edited_wording or "").strip():
        raise HTTPException(422, "edited_wording is required when action is edit.")
    rule_changed = False
    new_rule = None
    if body.action in {"accept", "edit"} and body.issue_type == "vague_rule" and body.rule_id and body.edited_wording:
        rule = await db.scalar(select(Rule).where(Rule.id == body.rule_id, Rule.workspace_id == user.workspace_id))
        if not rule:
            raise HTTPException(404, "Guideline rule not found.")
        if rule.status == "retired":
            raise HTTPException(409, "Retired rules cannot be reworded. Open the latest version of this rule.")
        # Rule wording changes go through normal versioning: the current rule stays in force
        # until a guideline owner confirms the new draft version (nothing changes automatically).
        latest = (await db.scalars(
            select(Rule).where(Rule.workspace_id == user.workspace_id, Rule.code == rule.code).order_by(Rule.version.desc())
        )).first()
        new_rule = Rule(
            workspace_id=user.workspace_id, document_id=rule.document_id, code=rule.code, title=rule.title,
            text=body.edited_wording.strip(), type=rule.type, severity=rule.severity, channels=list(rule.channels or []),
            status="draft", version=(latest.version if latest else rule.version) + 1, source_ref=rule.source_ref,
            created_by=user.id,
        )
        db.add(new_rule)
        await db.flush()
        for example in (await db.scalars(select(RuleExample).where(RuleExample.rule_id == rule.id))).all():
            db.add(RuleExample(rule_id=new_rule.id, kind=example.kind, text=example.text))
        await write_audit(
            db, user, "rule.version_created",
            {"previous_rule_id": rule.id, "rule_id": new_rule.id, "code": new_rule.code,
             "version": new_rule.version, "source": "guideline_health"},
        )
        rule_changed = True
    await write_audit(
        db, user, "guideline_health.issue_decided",
        {"issue_key": body.issue_key, "rule_id": body.rule_id, "issue_type": body.issue_type, "action": body.action,
         "edited_wording": body.edited_wording.strip() if body.edited_wording else None},
    )
    await db.commit()
    result = {"issue_key": body.issue_key, "action": body.action, "rule_changed": rule_changed}
    if new_rule is not None:
        result.update({
            "new_rule_id": new_rule.id, "new_rule_version": new_rule.version, "new_rule_status": "draft",
            "message": "A new draft version was created. The current rule stays active until a guideline owner confirms the draft.",
        })
    return result


@router.put('/workspace/model-mode')
async def set_workspace_model_mode(body: ModelModeInput, user: CurrentUser, db: DBSession):
    require_role(user, {"admin"})
    workspace = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    if not workspace:
        raise HTTPException(404, "Workspace not found.")
    settings_data = dict(workspace.settings or {})
    settings_data["model_mode"] = body.mode
    workspace.settings = settings_data
    await write_audit(
        db, user, "workspace.model_mode_changed",
        {"model_mode": body.mode},
    )
    await db.commit()
    return {"model_mode": body.mode}

@router.get('/precedents')
async def list_precedents(user: CurrentUser, db: DBSession):
    rows=(await db.scalars(select(Precedent).where(Precedent.workspace_id==user.workspace_id).order_by(Precedent.created_at.desc()))).all()
    return [{"id":p.id,"finding_id":p.finding_id,"rule_id":p.rule_id,"channel":p.channel,"pattern_text":p.pattern_text,"reason":p.reason,"valid_to":p.valid_to.isoformat() if p.valid_to else None,"status":p.status,"created_by":p.created_by,"approved_by":p.approved_by,"created_at":p.created_at.isoformat()} for p in rows]

@router.post('/precedents', status_code=201)
async def create_precedent(body: PrecedentInput, user: CurrentUser, db: DBSession):
    require_role(user, REVIEW_ROLES)
    finding=await db.scalar(select(ClaimFinding).where(ClaimFinding.id==body.finding_id,ClaimFinding.workspace_id==user.workspace_id))
    if not finding: raise HTTPException(404,'Finding not found in this workspace.')
    override = await db.scalar(
        select(FindingDecision.id).where(
            FindingDecision.finding_id == finding.id,
            FindingDecision.workspace_id == user.workspace_id,
            FindingDecision.action.in_(("override", "dispute")),
            func.length(func.trim(FindingDecision.reason)) > 0,
        ).limit(1)
    )
    if not override:
        raise HTTPException(409, "A reasoned reviewer override or dispute is required before saving a precedent.")
    content_item = await db.scalar(
        select(ContentItem).where(
            ContentItem.id == finding.content_id,
            ContentItem.workspace_id == user.workspace_id,
        )
    )
    if not content_item:
        raise HTTPException(404, "Content item not found.")
    channel = body.channel or content_item.channel
    if channel not in {"all", content_item.channel}:
        raise HTTPException(422, "A precedent channel must match the overridden content.")
    rule_id = body.rule_id
    if not rule_id:
        for evidence in finding.evidence or []:
            rule_id = evidence.get("rule_id")
            if not rule_id and evidence.get("code"):
                rule_id = await db.scalar(
                    select(Rule.id).where(
                        Rule.workspace_id == user.workspace_id,
                        Rule.code == evidence["code"],
                    ).order_by(Rule.version.desc()).limit(1)
                )
            if rule_id:
                break
    if not rule_id:
        raise HTTPException(422, "A precedent must be associated with the rule being overridden.")
    rule = await db.scalar(
        select(Rule).where(Rule.id == rule_id, Rule.workspace_id == user.workspace_id)
    )
    if not rule:
        raise HTTPException(404,'Rule not found in this workspace.')
    embedding = precedent_embedding(body.pattern_text.strip())
    p=Precedent(
        workspace_id=user.workspace_id,
        finding_id=finding.id,
        rule_id=rule_id,
        channel=channel,
        pattern_text=body.pattern_text.strip(),
        reason=body.reason.strip(),
        valid_to=body.valid_to,
        created_by=user.id,
        status='pending',
        embedding=embedding,
        scope_type="workspace",
        scope_id=user.workspace_id,
        scope={"rule_id": rule_id, "channel": channel},
    )
    db.add(p); await write_audit(db,user,'precedent.created',{'finding_id':finding.id,'precedent_status':'pending'})
    await db.commit(); await db.refresh(p)
    return {"id":p.id,"finding_id":p.finding_id,"rule_id":p.rule_id,"channel":p.channel,"pattern_text":p.pattern_text,"reason":p.reason,"status":p.status,"valid_to":p.valid_to.isoformat() if p.valid_to else None}


@router.get('/findings/{finding_id}/precedent-suggestions')
async def precedent_suggestions(finding_id: str, user: CurrentUser, db: DBSession):
    finding = await db.scalar(
        select(ClaimFinding).where(
            ClaimFinding.id == finding_id,
            ClaimFinding.workspace_id == user.workspace_id,
        )
    )
    if not finding:
        raise HTTPException(404, "Finding not found.")
    rule_ids = {
        evidence.get("rule_id") or evidence.get("id")
        for evidence in (finding.evidence or [])
        if evidence.get("rule_id") or evidence.get("id")
    }
    if not rule_ids:
        return {"finding_id": finding.id, "suggestions": []}
    item = await db.scalar(
        select(ContentItem).where(
            ContentItem.id == finding.content_id,
            ContentItem.workspace_id == user.workspace_id,
        )
    )
    if not item:
        raise HTTPException(404, "Content item not found.")
    rows = (await db.scalars(
        select(Precedent).where(
            Precedent.workspace_id == user.workspace_id,
            Precedent.status == "approved",
            Precedent.rule_id.in_(rule_ids),
            Precedent.scope_type == "workspace",
            (Precedent.valid_to.is_(None) | (Precedent.valid_to >= datetime.now(timezone.utc))),
            (Precedent.channel == "all") | (Precedent.channel == item.channel),
        )
    )).all()
    matches = []
    for rule_id in rule_ids:
        matches.extend(
            matching_approved_precedents(
                rows,
                rule_id=rule_id,
                channel=item.channel,
                pattern_text=finding.claim_text,
            )
        )
    suggestions = [
        precedent_suggestion(finding, precedent, score)
        for score, precedent in sorted(matches, key=lambda match: match[0], reverse=True)
    ]
    return {"finding_id": finding.id, "suggestions": suggestions}


@router.post('/findings/{finding_id}/precedent-suggestions/{precedent_id}/confirm')
async def confirm_precedent_suggestion(
    finding_id: str, precedent_id: str, user: CurrentUser, db: DBSession
):
    require_role(user, REVIEW_ROLES)
    finding = await db.scalar(
        select(ClaimFinding).where(
            ClaimFinding.id == finding_id,
            ClaimFinding.workspace_id == user.workspace_id,
        )
    )
    precedent = await db.scalar(
        select(Precedent).where(
            Precedent.id == precedent_id,
            Precedent.workspace_id == user.workspace_id,
            Precedent.status == "approved",
        )
    )
    if not finding or not precedent:
        raise HTTPException(404, "Finding or approved precedent not found.")
    if str(finding.severity).lower() == "critical":
        raise HTTPException(409, "Critical findings cannot be downgraded by precedent.")
    if finding.state not in {"open", "accepted"}:
        raise HTTPException(409, "Only an open finding can receive a precedent downgrade.")
    item = await db.scalar(
        select(ContentItem).where(
            ContentItem.id == finding.content_id,
            ContentItem.workspace_id == user.workspace_id,
        )
    )
    if (
        precedent.rule_id not in {
            evidence.get("rule_id") or evidence.get("id")
            for evidence in (finding.evidence or [])
        }
        or precedent.channel not in {"all", item.channel if item else None}
    ):
        raise HTTPException(409, "The precedent does not match this finding's rule and channel.")
    matches = matching_approved_precedents(
        [precedent],
        rule_id=precedent.rule_id,
        channel=item.channel,
        pattern_text=finding.claim_text,
    )
    if not matches:
        raise HTTPException(409, "The precedent does not meet the 0.85 similarity threshold.")
    finding.severity = "advisory"
    finding.evidence = list(finding.evidence or []) + [{
        "type": "precedent_downgrade_confirmed",
        "precedent_id": precedent.id,
        "similarity": round(matches[0][0], 4),
        "confirmed_by": user.id,
    }]
    await write_audit(
        db, user, "finding.precedent_downgrade_confirmed",
        {"finding_id": finding.id, "precedent_id": precedent.id, "severity": "advisory"},
    )
    await db.commit()
    return {"finding_id": finding.id, "severity": "advisory", "confirmed": True}

@router.post('/precedents/{precedent_id}/approve')
async def approve_precedent(precedent_id: str, user: CurrentUser, db: DBSession):
    require_role(user, OWNER_ROLES)
    p=await db.scalar(select(Precedent).where(Precedent.id==precedent_id,Precedent.workspace_id==user.workspace_id))
    if not p: raise HTTPException(404,'Precedent not found.')
    if p.status=='approved': raise HTTPException(409,'This precedent is already approved.')
    if p.status!='pending': raise HTTPException(409,'Only pending precedents can be approved.')
    p.status='approved'; p.approved_by=user.id; p.approved_at=datetime.now(timezone.utc)
    await write_audit(db,user,'precedent.approved',{'precedent_id':p.id,'finding_id':p.finding_id})
    await db.commit()
    return {"id":p.id,"status":p.status,"approved_by":p.approved_by,"approved_at":p.approved_at.isoformat()}

@router.post('/precedents/{precedent_id}/promote')
async def promote_precedent(precedent_id: str, user: CurrentUser, db: DBSession):
    require_role(user, OWNER_ROLES)
    precedent=await db.scalar(select(Precedent).where(Precedent.id==precedent_id,Precedent.workspace_id==user.workspace_id))
    if not precedent: raise HTTPException(404,'Precedent not found.')
    if precedent.status!='approved': raise HTTPException(409,'Only approved precedents can be promoted.')
    if precedent.valid_to and precedent.valid_to < datetime.now(timezone.utc): raise HTTPException(409,'Expired precedents cannot be promoted.')
    code=f"PREC-{precedent.id[:8].upper()}"
    previous=(await db.scalars(
        select(Rule).where(
            Rule.workspace_id==user.workspace_id,
            Rule.code==code,
        ).order_by(Rule.version.desc())
    )).first()
    if previous:
        previous.status = "retired"
    rule=Rule(workspace_id=user.workspace_id,code=code,title=f"Precedent: {precedent.pattern_text[:120]}",text=f"When this pattern applies: {precedent.pattern_text}\n\nApproved reviewer rationale: {precedent.reason}",type='brand_voice',severity='advisory',channels=[] if precedent.channel=='all' else [precedent.channel],status='draft',version=previous.version+1 if previous else 1,source_ref=f"Precedent {precedent.id}; manager-approved; requires guideline owner confirmation",created_by=user.id)
    db.add(rule); await write_audit(db,user,'precedent.promoted_to_draft_rule',{'precedent_id':precedent.id,'rule_code':code,'previous_rule_id':previous.id if previous else None})
    await db.commit(); await db.refresh(rule)
    return {'precedent_id':precedent.id,'rule_id':rule.id,'code':rule.code,'status':rule.status,'message':'Created as a draft rule. A guideline owner must confirm it before it becomes active.'}

@router.post('/content/{content_id}/verify-fix')
async def verify_fix(content_id: str, body: VerifyInput, user: CurrentUser, db: DBSession):
    """Run the same Claim Court engine against a temporary candidate revision, then roll it back."""
    from app.api.content import _perform_analysis
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    if item.status == 'approved': raise HTTPException(409,'Reopen approved content and create a new revision before verifying a fix.')
    rev=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not rev: raise HTTPException(409,'Current revision not found.')
    original_status=item.status; original_version=item.current_revision
    old_findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.revision_id==rev.id,ClaimFinding.workspace_id==user.workspace_id))).all()
    original_claims=[f.claim_text for f in old_findings if f.analysis_method not in {'layer1_deterministic','tone_heuristic'}]
    similarity=SequenceMatcher(None,rev.caption.lower(),body.proposed_text.lower()).ratio() if rev.caption or body.proposed_text else 1
    old_cta=bool(re.search(r"\b(buy|shop|order|book|sign up|learn more|link in bio|visit|register)\b",rev.caption,re.I))
    new_cta=bool(re.search(r"\b(buy|shop|order|book|sign up|learn more|link in bio|visit|register)\b",body.proposed_text,re.I))
    intent_check=measure_intent(rev.caption,body.proposed_text)
    latest_version=(await db.scalar(select(ContentRevision.version).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)).limit(1))) or original_version
    candidate=ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=latest_version+1,caption=body.proposed_text,alt_text=rev.alt_text,is_ai_media=rev.is_ai_media,paid_gifted=rev.paid_gifted,detected_language='unknown',creative_filename=rev.creative_filename,creative_storage_key=rev.creative_storage_key,ocr_text=rev.ocr_text,ocr_status=rev.ocr_status,image_analysis=rev.image_analysis,created_by=user.id)
    db.add(candidate); await db.flush()
    item.current_revision=candidate.version
    try:
        await _perform_analysis(db,user,item,candidate,None)
        candidate_findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.revision_id==candidate.id,ClaimFinding.workspace_id==user.workspace_id))).all()
        new_claims=[f.claim_text for f in candidate_findings if f.analysis_method not in {'layer1_deterministic','tone_heuristic','image_intelligence_v1'}]
        candidate_calls=(await db.scalars(select(AICall).where(AICall.workspace_id==user.workspace_id,AICall.revision_id==candidate.id))).all()
        for call in candidate_calls: call.revision_id=rev.id
        preserved=0
        unmatched=list(new_claims)
        for old in original_claims:
            match=next((new for new in unmatched if SequenceMatcher(None,old.lower(),new.lower()).ratio()>=0.72),None)
            if match is not None: preserved+=1; unmatched.remove(match)
        def critical_signature(finding):
            codes = {
                evidence.get("code") or evidence.get("rule_code")
                for evidence in (finding.evidence or [])
                if evidence.get("code") or evidence.get("rule_code")
            }
            return (re.sub(r"\W+", " ", finding.claim_text.casefold()).strip(), codes)
        baseline_critical = [
            critical_signature(finding)
            for finding in old_findings
            if finding.severity.lower() == "critical"
        ]
        new_critical=[]
        for finding in candidate_findings:
            if finding.severity.lower() != "critical":
                continue
            signature = critical_signature(finding)
            existing = any(
                SequenceMatcher(None, signature[0], old_text).ratio() >= 0.85
                and (not old_codes or not signature[1] or bool(old_codes & signature[1]))
                for old_text, old_codes in baseline_critical
            )
            if not existing:
                new_critical.append({'finding_id':finding.id,'verdict':finding.verdict,'severity':finding.severity,'claim_text':finding.claim_text,'rationale':finding.rationale})
        intent_preserved = (
            intent_check["intent_preserved"]
            and (not old_cta or new_cta)
        )
        def _norm_claim(text: str) -> str:
            return re.sub(r"\s+", " ", text.casefold()).strip()

        normalized_new_claims = {_norm_claim(new) for new in new_claims}
        changed_claims = [
            claim for claim in original_claims
            if _norm_claim(claim) not in normalized_new_claims
        ]
        result={'content_id':item.id,'source_revision_id':rev.id,'source_revision_version':rev.version,'candidate_text':body.proposed_text,'similarity':round(similarity,3),'embedding_similarity':intent_check["embedding_similarity"],'call_to_action_preserved':(not old_cta or new_cta),'original_claim_count':len(original_claims),'candidate_claim_count':len(new_claims),'intent_preserved_claim_count':preserved,'changed_claims':changed_claims,'intent_preserved':intent_preserved,'intent_check':intent_check,'full_engine_rerun':True,'candidate_findings':[{'claim_text':f.claim_text,'verdict':f.verdict,'severity':f.severity,'rationale':f.rationale,'evidence':f.evidence or []} for f in candidate_findings],'new_blocking_findings':new_critical,'safe_to_suggest':not new_critical and intent_preserved,'method':'deterministic_full_engine_candidate_revision','limitations':['Intent preservation uses a local hashing embedding and CTA retention, not human-level semantic equivalence.','Any new critical finding or intent-check failure rejects the suggestion; the candidate is never applied or approved.']}
        source_finding = None
        if body.finding_id:
            source_finding = await db.scalar(
                select(ClaimFinding).where(
                    ClaimFinding.id == body.finding_id,
                    ClaimFinding.workspace_id == user.workspace_id,
                    ClaimFinding.revision_id == rev.id,
                )
            )
            if not source_finding:
                raise HTTPException(404, "Finding is not part of the current revision.")
        elif old_findings:
            source_finding = old_findings[0]
        if source_finding:
            source_finding.intent_check = {
                **intent_check,
                "changed_claims": result["changed_claims"],
                "original_claim_count": len(original_claims),
                "candidate_claim_count": len(new_claims),
                "intent_preserved_claim_count": preserved,
                "intent_preserved": intent_preserved,
            }
        for finding in candidate_findings: await db.delete(finding)
        await db.delete(candidate)
        item.current_revision=original_version; item.status=original_status
        await write_audit(db,user,'fix.verification_run',{'content_id':item.id,'source_revision_id':rev.id,'safe_to_suggest':result['safe_to_suggest'],'intent_preserved':result['intent_preserved'],'intent_preserved_claim_count':preserved})
        await db.commit()
        return result
    except Exception:
        await db.rollback()
        raise


@router.post('/findings/{finding_id}/suggest-fix')
async def suggest_and_verify_fix(finding_id: str, user: CurrentUser, db: DBSession):
    finding = await db.scalar(
        select(ClaimFinding).where(
            ClaimFinding.id == finding_id,
            ClaimFinding.workspace_id == user.workspace_id,
        )
    )
    if not finding:
        raise HTTPException(404, "Finding not found.")
    item = await db.scalar(
        select(ContentItem).where(
            ContentItem.id == finding.content_id,
            ContentItem.workspace_id == user.workspace_id,
        )
    )
    if not item:
        raise HTTPException(404, "Content item not found.")
    revision = await db.scalar(
        select(ContentRevision).where(
            ContentRevision.content_id == item.id,
            ContentRevision.workspace_id == user.workspace_id,
            ContentRevision.version == item.current_revision,
        )
    )
    if not revision:
        raise HTTPException(409, "Current revision not found.")
    facts = (await db.scalars(
        select(Fact).where(
            Fact.workspace_id == user.workspace_id,
            Fact.status == "active",
            (Fact.valid_from.is_(None) | (Fact.valid_from <= datetime.now(timezone.utc))),
            (Fact.valid_to.is_(None) | (Fact.valid_to >= datetime.now(timezone.utc))),
        )
    )).all()
    workspace_settings = await _workspace_settings(db, user.workspace_id)
    model_mode = str(workspace_settings.get("model_mode") or settings.model_mode).lower()
    model_status = "not_requested"
    suggestion = generate_minimal_fix(revision.caption, finding.claim_text, facts)
    if model_mode == "ollama":
        raw_prompt = (
            f"CAPTION:\n{revision.caption}\n\nFLAGGED CLAIM:\n{finding.claim_text}\n\n"
            "APPROVED FACTS:\n"
            + "\n".join(
                f"{fact.id} | {fact.statement} | {fact.value} {fact.unit or ''}"
                for fact in facts
            )
        )
        try:
            masked, masked_count, local_map = mask_sensitive_with_map(
                raw_prompt, workspace_settings.get("secret_terms", [])
            )
            provider = configured_provider(settings, model_mode)
            attempt_started = {}
            attempt_calls = {}

            async def on_call(status: str, attempt: int):
                if status == "started":
                    attempt_started[attempt] = time.perf_counter()
                    attempt_calls[attempt] = await _log_model_call(
                        db, user.workspace_id, provider.name, provider.model,
                        "fix_suggestion", masked, masked_count, "started",
                    )
                    return
                elapsed = None
                if status in {"completed", "failed"} and attempt in attempt_started:
                    elapsed = round((time.perf_counter() - attempt_started.pop(attempt)) * 1000)
                call = attempt_calls.pop(attempt, None)
                if call:
                    call.status = status
                    call.duration_ms = elapsed

            model_suggestion = await validated_json(
                provider,
                system_prompt=(
                    "Suggest the smallest text edit that removes the flagged issue. Use only "
                    "the approved fact text supplied. Never add unsupported claims, change "
                    "personal/secret tokens, or approve content. Return candidate_text and the "
                    "matching source_fact_id, or null if no fact is used."
                ),
                user_prompt=masked,
                output_model=ModelFixSuggestion,
                on_call=on_call,
            )
            candidate_text = model_suggestion.candidate_text
            for token, original in local_map.items():
                candidate_text = candidate_text.replace(token, original)
            source_fact_id = model_suggestion.source_fact_id
            if source_fact_id and source_fact_id not in {fact.id for fact in facts}:
                raise ModelStepFailed("The model referenced a fact outside this workspace.")
            from app.services.fixes import FixSuggestion

            suggestion = FixSuggestion(
                candidate_text=candidate_text,
                source_fact_id=source_fact_id,
                method="ollama_full_engine_candidate",
            )
            model_status = "completed"
        except Exception:
            model_status = "needs_human_review"
    if not suggestion.candidate_text or suggestion.candidate_text == revision.caption:
        raise HTTPException(409, "No safe minimal edit could be generated for this finding.")
    verification = await verify_fix(
        item.id,
        VerifyInput(proposed_text=suggestion.candidate_text, finding_id=finding.id),
        user,
        db,
    )
    accepted = bool(verification["safe_to_suggest"]) and model_status != "needs_human_review"
    if accepted:
        finding.suggested_fix = suggestion.candidate_text
    await write_audit(
        db, user, "finding.fix_suggestion_verified",
        {
            "finding_id": finding.id,
            "source_fact_id": suggestion.source_fact_id,
            "method": suggestion.method,
            "accepted": accepted,
            "model_status": model_status,
            "intent_preserved": verification["intent_preserved"],
            "new_critical_count": len(verification["new_blocking_findings"]),
        },
    )
    await db.commit()
    return {
        "finding_id": finding.id,
        "suggested_fix": suggestion.candidate_text if accepted else None,
        "source_fact_id": suggestion.source_fact_id,
        "method": suggestion.method,
        "accepted": accepted,
        "model_status": model_status,
        "rejection_reason": None if accepted else (
            "The full engine found a new critical finding or the intent-preservation checks failed."
        ),
        "verification": verification,
    }

@router.get('/insights')
async def insights(user: CurrentUser, db: DBSession):
    items=(await db.scalars(select(ContentItem).where(ContentItem.workspace_id==user.workspace_id))).all()
    findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.workspace_id==user.workspace_id))).all()
    decisions=(await db.scalars(select(FindingDecision).where(FindingDecision.workspace_id==user.workspace_id))).all()
    rules=(await db.scalars(select(Rule).where(Rule.workspace_id==user.workspace_id))).all()
    events=(await db.scalars(select(AuditEvent).where(AuditEvent.workspace_id==user.workspace_id).order_by(AuditEvent.created_at))).all()
    top_codes={}
    for f in findings:
        for e in f.evidence or []:
            code=e.get('code') or e.get('rule_code')
            if code: top_codes[code]=top_codes.get(code,0)+1
    by_status={}; by_channel={}; by_verdict={}
    item_by_id={i.id:i for i in items}
    for i in items:
        by_status[i.status]=by_status.get(i.status,0)+1
        by_channel[i.channel]=by_channel.get(i.channel,0)+1
    for f in findings: by_verdict[f.verdict]=by_verdict.get(f.verdict,0)+1
    overrides=sum(1 for d in decisions if d.action=='override')
    disputes=sum(1 for d in decisions if d.action=='dispute')
    created_at={}; approval_durations=[]; review_rounds={}
    for event in events:
        payload=event.payload or {}; cid=payload.get('content_id')
        if event.type=='content.created' and cid:
            created_at[cid]=event.created_at
        if event.type=='content.workflow_changed' and cid:
            if payload.get('status')=='in_review':
                review_rounds[cid]=review_rounds.get(cid,0)+1
            if payload.get('status')=='approved' and cid and cid in created_at:
                seconds=(event.created_at-created_at[cid]).total_seconds()
                if seconds>=0: approval_durations.append(seconds)
    # Attribute override/dispute actions to the evidence codes on their finding, when available.
    decision_by_finding={}
    for d in decisions:
        if d.action not in {'override','dispute'}: continue
        decision_by_finding.setdefault(d.finding_id,[]).append(d.action)
    issue_decisions={}
    finding_by_id={f.id:f for f in findings}
    for fid, actions in decision_by_finding.items():
        finding=finding_by_id.get(fid)
        if not finding: continue
        for evidence in finding.evidence or []:
            code=evidence.get('code') or evidence.get('rule_code')
            if code:
                bucket=issue_decisions.setdefault(code,{'overrides':0,'disputes':0})
                bucket['overrides']+=actions.count('override'); bucket['disputes']+=actions.count('dispute')
    review_round_values=list(review_rounds.values())
    return {
        'items_total':len(items),'findings_total':len(findings),'decisions_total':len(decisions),
        'overrides':overrides,'disputes':disputes,'by_status':by_status,'by_channel':by_channel,
        'by_verdict':by_verdict,
        'top_evidence_codes':[{'code':k,'count':v} for k,v in sorted(top_codes.items(),key=lambda x:x[1],reverse=True)[:8]],
        'override_dispute_by_code':[{'code':k,**v} for k,v in sorted(issue_decisions.items(),key=lambda x:x[1]['overrides']+x[1]['disputes'],reverse=True)[:8]],
        'approved_items_with_timing':len(approval_durations),
        'average_upload_to_approval_seconds':round(sum(approval_durations)/len(approval_durations),1) if approval_durations else None,
        'average_review_rounds':round(sum(review_round_values)/len(review_round_values),2) if review_round_values else None,
        'active_rules':sum(1 for r in rules if r.status=='active'),
        'model_mode':settings.model_mode.lower(),
        'note':'Metrics reflect currently retained workspace records. Timing depends on audit events captured since content creation. These are operational insights, not model accuracy results.'
    }
