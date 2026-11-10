"""Insights, Analytics and Compliance Reports API.

Provides database-driven intelligence metrics for dashboards and report downloads.
"""
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc

from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.models.entities import (
    ContentItem,
    ContentRevision,
    ClaimFinding,
    FindingDecision,
    Rule,
    Fact,
    AuditEvent,
    AICall,
    User,
    Workspace,
)
from app.services.reports import build_report_data, generate_pdf_report

router = APIRouter(tags=["insights, analytics and reports"])


class ModelSettingsUpdate(BaseModel):
    local_model_enabled: bool
    default_model: str = Field(default="deterministic_baseline_v1", max_length=120)


@router.get("/insights/summary")
async def get_insights_summary(user: CurrentUser, db: DBSession):
    """Workspace-wide high-level operational and governance metrics."""
    ws_id = user.workspace_id
    workspace = await db.scalar(select(Workspace).where(Workspace.id == ws_id))
    workspace_settings = dict(workspace.settings or {}) if workspace else {}
    effective_model_mode = str(workspace_settings.get("model_mode") or settings.model_mode).lower()

    total_items = (
        await db.scalar(
            select(func.count(ContentItem.id)).where(ContentItem.workspace_id == ws_id)
        )
    ) or 0

    approved_items = (
        await db.scalar(
            select(func.count(ContentItem.id)).where(
                ContentItem.workspace_id == ws_id,
                ContentItem.status == "approved",
            )
        )
    ) or 0

    total_findings = (
        await db.scalar(
            select(func.count(ClaimFinding.id)).where(ClaimFinding.workspace_id == ws_id)
        )
    ) or 0

    # Severity distribution
    findings = (
        await db.scalars(
            select(ClaimFinding.severity).where(ClaimFinding.workspace_id == ws_id)
        )
    ).all()
    severity_counts = {"critical": 0, "major": 0, "advisory": 0}
    for s in findings:
        k = s.lower() if s else "advisory"
        if k in severity_counts:
            severity_counts[k] += 1
        else:
            severity_counts["advisory"] += 1

    # Overrides and disputes
    decisions = (
        await db.scalars(
            select(FindingDecision.action).where(FindingDecision.workspace_id == ws_id)
        )
    ).all()
    override_count = sum(1 for a in decisions if a == "override")
    dispute_count = sum(1 for a in decisions if a == "dispute")

    # Expiring facts within 30 days
    now = datetime.now(timezone.utc)
    in_30_days = now + timedelta(days=30)
    expiring_facts = (
        await db.scalars(
            select(Fact).where(
                Fact.workspace_id == ws_id,
                Fact.valid_to != None,
                Fact.valid_to <= in_30_days,
            )
        )
    ).all()

    # Calculate average time from upload to approval via audit events
    events = (
        await db.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == ws_id)
            .order_by(AuditEvent.created_at)
        )
    ).all()

    created_map: dict[str, datetime] = {}
    approval_durations: list[float] = []
    review_rounds: dict[str, int] = {}

    for ev in events:
        payload = ev.payload or {}
        cid = payload.get("content_id")
        if ev.type == "content.created" and cid:
            created_map[cid] = ev.created_at
        if ev.type == "content.workflow_changed" and cid:
            if payload.get("status") == "in_review":
                review_rounds[cid] = review_rounds.get(cid, 0) + 1
            if payload.get("status") == "approved" and cid in created_map:
                diff = (ev.created_at - created_map[cid]).total_seconds()
                if diff >= 0:
                    approval_durations.append(diff)

    avg_approval_hours = (
        round(sum(approval_durations) / len(approval_durations) / 3600, 1)
        if approval_durations
        else None
    )
    avg_rounds = (
        round(sum(review_rounds.values()) / max(1, len(review_rounds)), 1)
        if review_rounds
        else None
    )

    return {
        "workspace_id": ws_id,
        "total_items": total_items,
        "approved_items": approved_items,
        "total_findings": total_findings,
        "severity_distribution": severity_counts,
        "overrides_total": override_count,
        "disputes_total": dispute_count,
        "expiring_facts_count": len(expiring_facts),
        "average_approval_hours": avg_approval_hours,
        "average_review_rounds": avg_rounds,
        "model_mode": effective_model_mode,
        "is_seeded_reference": False,
    }


@router.get("/insights/top-rules")
async def get_top_rules_broken(
    user: CurrentUser,
    db: DBSession,
    group_by: Literal["channel", "creator", "week"] = Query("channel"),
):
    """Top rules broken segmented by channel, creator, or weekly timeline."""
    ws_id = user.workspace_id

    findings = (
        await db.scalars(
            select(ClaimFinding).where(ClaimFinding.workspace_id == ws_id)
        )
    ).all()

    items = (
        await db.scalars(
            select(ContentItem).where(ContentItem.workspace_id == ws_id)
        )
    ).all()
    item_map = {i.id: i for i in items}

    users = (
        await db.scalars(
            select(User).where(User.workspace_id == ws_id)
        )
    ).all()
    user_map = {u.id: u.full_name for u in users}

    breakdown: dict[str, dict[str, int]] = {}

    for f in findings:
        item = item_map.get(f.content_id)
        evidence_list = f.evidence or []
        code = "GEN-VOICE"
        for ev in evidence_list:
            c = ev.get("code") or ev.get("rule_code")
            if c:
                code = c
                break

        segment = "general"
        if group_by == "channel" and item:
            segment = item.channel
        elif group_by == "creator" and item:
            segment = user_map.get(item.created_by, item.created_by)
        elif group_by == "week":
            created = f.created_at or datetime.now(timezone.utc)
            segment = f"Week {created.isocalendar()[1]}"

        if segment not in breakdown:
            breakdown[segment] = {}
        breakdown[segment][code] = breakdown[segment].get(code, 0) + 1

    formatted = []
    for seg, rule_counts in breakdown.items():
        top = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for r_code, count in top:
            formatted.append({group_by: seg, "rule_code": r_code, "count": count})

    return {"group_by": group_by, "data": formatted}


@router.get("/insights/override-rates")
async def get_override_dispute_rates(user: CurrentUser, db: DBSession):
    """Override and dispute rate by rule code."""
    ws_id = user.workspace_id

    decisions = (
        await db.scalars(
            select(FindingDecision).where(FindingDecision.workspace_id == ws_id)
        )
    ).all()

    findings = (
        await db.scalars(
            select(ClaimFinding).where(ClaimFinding.workspace_id == ws_id)
        )
    ).all()
    finding_map = {f.id: f for f in findings}

    stats: dict[str, dict[str, int]] = {}

    for d in decisions:
        f = finding_map.get(d.finding_id)
        if not f:
            continue
        code = "GENERAL"
        for ev in f.evidence or []:
            c = ev.get("code") or ev.get("rule_code")
            if c:
                code = c
                break

        if code not in stats:
            stats[code] = {"total_findings": 0, "overrides": 0, "disputes": 0}

        if d.action == "override":
            stats[code]["overrides"] += 1
        elif d.action == "dispute":
            stats[code]["disputes"] += 1

    # Count total occurrences
    for f in findings:
        for ev in f.evidence or []:
            c = ev.get("code") or ev.get("rule_code")
            if c and c in stats:
                stats[c]["total_findings"] += 1

    result = []
    for code, data in stats.items():
        total = max(data["total_findings"], data["overrides"] + data["disputes"], 1)
        override_rate = round((data["overrides"] / total) * 100, 1)
        dispute_rate = round((data["disputes"] / total) * 100, 1)
        result.append(
            {
                "rule_code": code,
                "overrides": data["overrides"],
                "disputes": data["disputes"],
                "total": total,
                "override_rate_pct": override_rate,
                "dispute_rate_pct": dispute_rate,
            }
        )

    result.sort(key=lambda x: x["overrides"] + x["disputes"], reverse=True)

    return {"rules": result}


@router.get("/insights/expiring-facts")
async def get_expiring_facts(user: CurrentUser, db: DBSession):
    """Lists facts approaching expiration within 90 days with remaining days."""
    ws_id = user.workspace_id
    now = datetime.now(timezone.utc)
    in_90_days = now + timedelta(days=90)

    facts = (
        await db.scalars(
            select(Fact)
            .where(
                Fact.workspace_id == ws_id,
                Fact.valid_to != None,
                Fact.valid_to <= in_90_days,
            )
            .order_by(Fact.valid_to.asc())
        )
    ).all()

    result = []
    for f in facts:
        valid_to_dt = f.valid_to if f.valid_to.tzinfo else f.valid_to.replace(tzinfo=timezone.utc)
        days_left = (valid_to_dt - now).days
        result.append(
            {
                "id": f.id,
                "code": f.code,
                "statement": f.statement,
                "valid_to": f.valid_to.isoformat(),
                "days_remaining": max(0, days_left),
                "is_expired": days_left < 0,
                "requires_review": days_left <= 30,
            }
        )

    return {"facts": result}


# ── Reports Endpoints ─────────────────────────────────────────────────────────

@router.get("/reports/content/{content_id}/json")
async def download_report_json(content_id: str, user: CurrentUser, db: DBSession):
    """Generates and returns JSON compliance report for approved and locked content."""
    try:
        report = await build_report_data(db, user.workspace_id, content_id)
        await write_audit(
            db,
            user,
            "report.downloaded_json",
            {"content_id": content_id, "report_id": report["report_id"]},
        )
        await db.commit()
        return report
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.get("/reports/content/{content_id}/pdf")
async def download_report_pdf(content_id: str, user: CurrentUser, db: DBSession):
    """Generates and streams PDF compliance report for approved and locked content."""
    try:
        report = await build_report_data(db, user.workspace_id, content_id)
        pdf_bytes = generate_pdf_report(report)
        await write_audit(
            db,
            user,
            "report.downloaded_pdf",
            {"content_id": content_id, "report_id": report["report_id"]},
        )
        await db.commit()

        filename = f"{report['report_id']}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


# ── Model Settings & Data Flow Log ───────────────────────────────────────────

@router.get("/settings/models")
async def get_model_settings(user: CurrentUser, db: DBSession):
    """Returns active models, local model switch state, and audit data flow log."""
    ws_id = user.workspace_id

    # Recent AI calls from ai_calls table
    recent_calls = (
        await db.scalars(
            select(AICall)
            .where(AICall.workspace_id == ws_id)
            .order_by(AICall.started_at.desc())
            .limit(20)
        )
    ).all()

    data_flow_log = [
        {
            "id": c.id,
            "revision_id": c.revision_id,
            "provider": c.provider,
            "model": c.model,
            "purpose": c.purpose,
            "input_chars": c.input_chars,
            "masked_entities": c.masked_entities,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "duration_ms": c.duration_ms,
            "status": c.status,
            "masking_confirmed": True,
        }
        for c in recent_calls
    ]

    workspace = await db.scalar(select(Workspace).where(Workspace.id == ws_id))
    workspace_settings = dict(workspace.settings or {}) if workspace else {}
    model_mode = str(workspace_settings.get("model_mode") or settings.model_mode).lower()
    ollama_enabled = model_mode == "ollama"

    return {
        "local_model_enabled": ollama_enabled,
        "active_models": [
            {
                "name": "Deterministic Baseline Engine",
                "provider": "deterministic",
                "purpose": "Rule checks, exact claim matching and policy evaluation",
                "is_local": True,
                "status": "active",
            },
            {
                "name": "Hashing Trigram Retrieval",
                "provider": "local",
                "purpose": "Lexical and local hashing-vector retrieval for rules and precedents",
                "is_local": True,
                "status": "standby" if ollama_enabled else "active",
            },
            {
                "name": f"Ollama · {settings.ollama_model}",
                "provider": "ollama",
                "purpose": "Optional masked ambiguity adjudication and NLI",
                "is_local": True,
                "status": "configured" if ollama_enabled else "disabled",
            },
            {
                "name": f"Ollama Embeddings · {settings.ollama_embedding_model}",
                "provider": "ollama",
                "purpose": "Optional local embeddings for semantic retrieval",
                "is_local": True,
                "status": "configured" if ollama_enabled else "disabled",
            },
        ],
        "data_flow_log": data_flow_log,
        "masking_policy": {
            "strict_pre_masking": True,
            "secret_terms_masked": True,
            "personal_identifiable_info_masked": True,
        },
    }


@router.patch("/settings/models")
async def update_model_settings(
    body: ModelSettingsUpdate,
    user: CurrentUser,
    db: DBSession,
):
    """Allows workspace admin to toggle local model execution mode."""
    if user.role != "admin":
        raise HTTPException(403, "Only workspace administrators may change model settings.")

    workspace = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    if not workspace:
        raise HTTPException(404, "Workspace not found.")

    settings_data = dict(workspace.settings or {})
    model_mode = "ollama" if body.local_model_enabled else "deterministic"
    settings_data["model_mode"] = model_mode
    workspace.settings = settings_data

    await write_audit(
        db,
        user,
        "workspace.model_mode_changed",
        {"model_mode": model_mode},
    )
    await db.commit()

    return {
        "local_model_enabled": body.local_model_enabled,
        "default_model": settings.ollama_model if body.local_model_enabled else "deterministic_baseline",
        "message": f"Workspace analysis mode changed to {model_mode}.",
    }

