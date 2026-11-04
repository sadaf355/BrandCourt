"""Phase 8–10: guideline health, precedent ledger, fix verification and insights."""
from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.models.entities import Rule, Fact, ContentItem, ContentRevision, ClaimFinding, FindingDecision, Precedent, AuditEvent, AICall

router = APIRouter(tags=["guideline health, precedents and verification"])
OWNER_ROLES = {"manager", "admin"}
REVIEW_ROLES = {"reviewer", "manager", "admin"}
def require_role(user, roles):
    if user.role not in roles: raise HTTPException(403, "Your workspace role does not permit this action.")

class PrecedentInput(BaseModel):
    finding_id: str
    rule_id: str | None = None
    channel: str = Field(default="all", max_length=40)
    pattern_text: str = Field(min_length=3, max_length=2000)
    reason: str = Field(min_length=3, max_length=3000)
    valid_to: datetime | None = None

class VerifyInput(BaseModel):
    proposed_text: str = Field(min_length=1, max_length=20000)

@router.get('/guideline-health')
async def guideline_health(user: CurrentUser, db: DBSession):
    rules = (await db.scalars(select(Rule).where(Rule.workspace_id==user.workspace_id, Rule.status=='active'))).all()
    issues=[]
    vague = ("appropriate", "as needed", "good quality", "professional", "suitable", "high quality", "best possible")
    for r in rules:
        text=f"{r.title} {r.text}".lower()
        hits=[term for term in vague if term in text]
        if hits:
            issues.append({"type":"vague_rule","severity":"major","rule_id":r.id,"code":r.code,"title":r.title,"explanation":f"Potentially subjective wording: {', '.join(hits)}.","suggestion":"Replace subjective wording with a measurable condition, threshold, or concrete example."})
        if len(r.text.strip()) < 24:
            issues.append({"type":"underspecified_rule","severity":"major","rule_id":r.id,"code":r.code,"title":r.title,"explanation":"The rule is very short and may not explain when it applies.","suggestion":"Add scope, channel, severity, and a positive/negative example."})
    # Flag similar rule pairs as candidates, not proven contradictions.
    for i, a in enumerate(rules):
        aw=set(re.findall(r"[a-z0-9]+", f"{a.title} {a.text}".lower()))
        for b in rules[i+1:]:
            if a.channels and b.channels and not set(a.channels).intersection(b.channels): continue
            bw=set(re.findall(r"[a-z0-9]+", f"{b.title} {b.text}".lower()))
            union=aw|bw; similarity=len(aw&bw)/len(union) if union else 0
            opposite=any(x in f" {a.text.lower()} " for x in [" must "," always "]) and any(x in f" {b.text.lower()} " for x in [" must not "," never "])
            if similarity >= .38 or opposite:
                issues.append({"type":"possible_conflict","severity":"review","rule_id":a.id,"other_rule_id":b.id,"code":f"{a.code} / {b.code}","title":f"{a.title} ↔ {b.title}","explanation":f"Rules share scope or wording (lexical similarity {similarity:.0%}); this is a candidate for human review, not a confirmed contradiction.","suggestion":"Compare the rules' intent, scope and priority; clarify or consolidate if they conflict."})
    issues.sort(key=lambda x: (0 if x['severity']=='major' else 1, x['type']))
    return {"active_rules":len(rules),"issue_count":len(issues),"issues":issues,"method":"heuristic_v1","notice":"Heuristic screening only. Similarity does not prove a contradiction; a guideline owner must decide."}

@router.get('/precedents')
async def list_precedents(user: CurrentUser, db: DBSession):
    rows=(await db.scalars(select(Precedent).where(Precedent.workspace_id==user.workspace_id).order_by(Precedent.created_at.desc()))).all()
    return [{"id":p.id,"finding_id":p.finding_id,"rule_id":p.rule_id,"channel":p.channel,"pattern_text":p.pattern_text,"reason":p.reason,"valid_to":p.valid_to.isoformat() if p.valid_to else None,"status":p.status,"created_by":p.created_by,"approved_by":p.approved_by,"created_at":p.created_at.isoformat()} for p in rows]

@router.post('/precedents', status_code=201)
async def create_precedent(body: PrecedentInput, user: CurrentUser, db: DBSession):
    require_role(user, REVIEW_ROLES)
    finding=await db.scalar(select(ClaimFinding).where(ClaimFinding.id==body.finding_id,ClaimFinding.workspace_id==user.workspace_id))
    if not finding: raise HTTPException(404,'Finding not found in this workspace.')
    if body.rule_id and not await db.scalar(select(Rule.id).where(Rule.id==body.rule_id,Rule.workspace_id==user.workspace_id)):
        raise HTTPException(404,'Rule not found in this workspace.')
    p=Precedent(workspace_id=user.workspace_id,finding_id=finding.id,rule_id=body.rule_id,channel=body.channel,pattern_text=body.pattern_text.strip(),reason=body.reason.strip(),valid_to=body.valid_to,created_by=user.id,status='pending')
    db.add(p); await write_audit(db,user,'precedent.created',{'finding_id':finding.id,'precedent_status':'pending'})
    await db.commit(); await db.refresh(p)
    return {"id":p.id,"finding_id":p.finding_id,"rule_id":p.rule_id,"channel":p.channel,"pattern_text":p.pattern_text,"reason":p.reason,"status":p.status,"valid_to":p.valid_to.isoformat() if p.valid_to else None}

@router.post('/precedents/{precedent_id}/approve')
async def approve_precedent(precedent_id: str, user: CurrentUser, db: DBSession):
    require_role(user, OWNER_ROLES)
    p=await db.scalar(select(Precedent).where(Precedent.id==precedent_id,Precedent.workspace_id==user.workspace_id))
    if not p: raise HTTPException(404,'Precedent not found.')
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
    existing=(await db.scalars(select(Rule).where(Rule.workspace_id==user.workspace_id,Rule.code.like('PREC-%')))).all()
    code=f"PREC-{precedent.id[:8].upper()}"
    rule=Rule(workspace_id=user.workspace_id,code=code,title=f"Precedent: {precedent.pattern_text[:120]}",text=precedent.reason,type='brand_voice',severity='warning',channels=[] if precedent.channel=='all' else [precedent.channel],status='draft',version=1,source_ref=f"Precedent {precedent.id}; manager-approved; requires guideline owner confirmation",created_by=user.id)
    db.add(rule); await write_audit(db,user,'precedent.promoted_to_draft_rule',{'precedent_id':precedent.id,'rule_code':code})
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
    latest_version=(await db.scalar(select(ContentRevision.version).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)).limit(1))) or original_version
    candidate=ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=latest_version+1,caption=body.proposed_text,alt_text=rev.alt_text,is_ai_media=rev.is_ai_media,detected_language='unknown',creative_filename=rev.creative_filename,creative_storage_key=rev.creative_storage_key,ocr_text=rev.ocr_text,ocr_status=rev.ocr_status,image_analysis=rev.image_analysis,created_by=user.id)
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
        new_critical=[{'finding_id':f.id,'verdict':f.verdict,'severity':f.severity,'claim_text':f.claim_text,'rationale':f.rationale} for f in candidate_findings if f.severity.lower() in {'critical','blocker'} or f.verdict.lower() in {'contradicted','outdated','unsupported'}]
        result={'content_id':item.id,'source_revision_id':rev.id,'source_revision_version':rev.version,'candidate_text':body.proposed_text,'similarity':round(similarity,3),'call_to_action_preserved':(not old_cta or new_cta),'original_claim_count':len(original_claims),'candidate_claim_count':len(new_claims),'intent_preserved_claim_count':preserved,'intent_preserved':preserved>=max(1,len(original_claims)) and (not old_cta or new_cta),'full_engine_rerun':True,'candidate_findings':[{'claim_text':f.claim_text,'verdict':f.verdict,'severity':f.severity,'rationale':f.rationale,'evidence':f.evidence or []} for f in candidate_findings],'new_blocking_findings':new_critical,'safe_to_suggest':not new_critical,'method':'deterministic_full_engine_candidate_revision','limitations':['Intent preservation is based on claim-text matching and CTA retention, not human-level semantic equivalence.','Any new blocking finding requires human review; the candidate is not automatically applied or approved.']}
        for finding in candidate_findings: await db.delete(finding)
        await db.delete(candidate)
        item.current_revision=original_version; item.status=original_status
        await write_audit(db,user,'fix.verification_run',{'content_id':item.id,'source_revision_id':rev.id,'safe_to_suggest':result['safe_to_suggest'],'intent_preserved':result['intent_preserved'],'intent_preserved_claim_count':preserved})
        await db.commit()
        return result
    except Exception:
        await db.rollback()
        raise

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
