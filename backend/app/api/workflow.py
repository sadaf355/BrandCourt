import asyncio
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.storage import get_storage
from app.models.entities import ContentItem, ContentRevision, ClaimFinding, ReviewComment, FindingDecision, ReviewJob
from app.services.claim_policy import is_approval_blocker, decision_clears_approval_block

router = APIRouter(tags=['image intelligence and review workflow'])
REVIEW_ROLES = {'reviewer', 'manager', 'admin'}
MANAGER_ROLES = {'manager', 'admin'}

def require_role(user, roles):
    if user.role not in roles: raise HTTPException(403, 'Your workspace role does not permit this action.')

class CommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    finding_id: str | None = None
class DecisionInput(BaseModel):
    action: str = Field(pattern='^(accept|edit|dispute|override|resolve)$')
    reason: str = Field(default='', max_length=3000)
    edited_text: str | None = Field(default=None, min_length=1, max_length=30000)
class StateInput(BaseModel):
    action: str = Field(pattern='^(submit|start_review|approve|reject|reopen)$')
    reason: str = Field(default='', max_length=3000)

def _run_stored_tesseract_ocr(storage, storage_key: str) -> str:
    """Materialize the object and run Pillow/Tesseract outside the event loop."""
    from PIL import Image
    import pytesseract

    with storage.materialize(storage_key) as image_path:
        with Image.open(image_path) as image:
            if image.width * image.height > 40_000_000:
                raise HTTPException(413, 'Image dimensions exceed the 40 megapixel OCR safety limit.')
            return pytesseract.image_to_string(image.convert('RGB'), timeout=15).strip()


def comment_view(c, user_name='Team member'):
    return {'id':c.id,'content_id':c.content_id,'finding_id':c.finding_id,'user_id':c.user_id,'user_name':user_name,'body':c.body,'created_at':c.created_at.isoformat()}

async def get_item(content_id, user, db):
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id, ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404, 'Content item not found.')
    return item

@router.post('/content/{content_id}/ocr')
async def run_ocr(content_id: str, user: CurrentUser, db: DBSession):
    item=await get_item(content_id,user,db)
    rev=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not rev: raise HTTPException(409,'No current revision exists.')
    if item.status == 'approved' or rev.locked_at is not None: raise HTTPException(409,'Approved revision is locked. Reopen the item before rerunning OCR.')
    if not rev.creative_storage_key: raise HTTPException(409,'Attach an image creative before running OCR.')
    suffix=Path(rev.creative_storage_key).suffix.lower()
    if suffix=='.svg':
        rev.ocr_text=''; rev.ocr_status='unsupported_vector'
        result={'status':'unsupported_vector','text':'','message':'OCR is only enabled for raster images (PNG, JPG, WEBP, GIF). SVG remains attached but must be exported to a raster image for OCR.'}
    else:
        try:
            text = await asyncio.to_thread(
                _run_stored_tesseract_ocr, get_storage(), rev.creative_storage_key
            )
            rev.ocr_text=text; rev.ocr_status='completed' if text else 'no_text_found'
            result={'status':rev.ocr_status,'text':text,'message':'Extracted image text is included in the next Claim Court run.' if text else 'No text was detected. Text checks can still run on the caption.'}
        except ImportError:
            rev.ocr_text=''; rev.ocr_status='unavailable'
            result={'status':'unavailable','text':'','message':'OCR dependencies are not installed. Install Pillow and pytesseract, plus the Tesseract OCR engine, then retry.'}
        except HTTPException: raise
        except Exception as exc:
            rev.ocr_text=''; rev.ocr_status='failed'
            result={'status':'failed','text':'','message':f'OCR could not process this image ({type(exc).__name__}).'}
    await write_audit(db,user,'creative.ocr_completed',{'content_id':item.id,'revision_id':rev.id,'status':result['status']})
    await db.commit()
    return {**result,'revision_id':rev.id,'revision_version':rev.version}

@router.get('/content/{content_id}/comments')
async def list_comments(content_id: str, user: CurrentUser, db: DBSession):
    await get_item(content_id,user,db)
    rows=(await db.scalars(select(ReviewComment).where(ReviewComment.content_id==content_id,ReviewComment.workspace_id==user.workspace_id).order_by(ReviewComment.created_at))).all()
    from app.models.entities import User
    result=[]
    for row in rows:
        actor=await db.get(User,row.user_id)
        result.append(comment_view(row, actor.full_name if actor else 'Former member'))
    return result

@router.post('/content/{content_id}/comments', status_code=201)
async def add_comment(content_id: str, body: CommentInput, user: CurrentUser, db: DBSession):
    await get_item(content_id,user,db)
    if body.finding_id and not await db.scalar(select(ClaimFinding.id).where(ClaimFinding.id==body.finding_id,ClaimFinding.content_id==content_id,ClaimFinding.workspace_id==user.workspace_id)):
        raise HTTPException(404,'Finding not found in this workspace item.')
    row=ReviewComment(workspace_id=user.workspace_id,content_id=content_id,finding_id=body.finding_id,user_id=user.id,body=body.body.strip())
    db.add(row); await write_audit(db,user,'review.comment_added',{'content_id':content_id,'finding_id':body.finding_id})
    await db.commit(); await db.refresh(row)
    return comment_view(row,user.full_name)

@router.post('/findings/{finding_id}/decision', status_code=201)
async def decide_finding(finding_id: str, body: DecisionInput, background_tasks: BackgroundTasks, user: CurrentUser, db: DBSession):
    if body.action in {'accept','edit','dispute'}:
        require_role(user, {'creator','reviewer','manager','admin'})
    else:
        require_role(user, REVIEW_ROLES)
    if body.action == 'override' and not body.reason.strip():
        raise HTTPException(422, 'A reason is required when overriding a finding.')
    if body.action == 'edit' and not (body.edited_text or '').strip():
        raise HTTPException(422, 'edited_text is required when editing a finding.')
    finding=await db.scalar(select(ClaimFinding).where(ClaimFinding.id==finding_id,ClaimFinding.workspace_id==user.workspace_id))
    if not finding: raise HTTPException(404,'Finding not found.')
    locked_revision = await db.scalar(select(ContentRevision.id).where(ContentRevision.id==finding.revision_id,ContentRevision.locked_at.is_not(None)))
    if locked_revision:
        raise HTTPException(409, 'This finding belongs to an approved, locked revision. Reopen the content before changing its decisions.')
    india_codes={e.get('code') for e in (finding.evidence or []) if e.get('type')=='policy_pack' and str(e.get('code','')).startswith('IN-')}
    if body.action=='override' and india_codes:
        require_role(user, MANAGER_ROLES)
    item=await db.scalar(select(ContentItem).where(ContentItem.id==finding.content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    row=FindingDecision(workspace_id=user.workspace_id,finding_id=finding.id,user_id=user.id,action=body.action,reason=body.reason.strip())
    db.add(row)
    state_map={'accept':'accepted','edit':'edited','dispute':'disputed','override':'overridden','resolve':'resolved'}
    finding.state=state_map[body.action]
    queued=None
    if body.action=='edit':
        current=await db.scalar(select(ContentRevision).where(ContentRevision.id==finding.revision_id,ContentRevision.workspace_id==user.workspace_id))
        if not current: raise HTTPException(409,'Source revision is missing.')
        latest_version=(await db.scalar(select(ContentRevision.version).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)).limit(1))) or current.version
        revision=ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=latest_version+1,caption=body.edited_text.strip(),alt_text=current.alt_text,is_ai_media=current.is_ai_media,detected_language='unknown',creative_filename=current.creative_filename,creative_storage_key=current.creative_storage_key,ocr_text=current.ocr_text,ocr_status=current.ocr_status,image_analysis=current.image_analysis,created_by=user.id)
        db.add(revision); await db.flush(); item.current_revision=revision.version; item.status='draft'
        queued=ReviewJob(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,created_by=user.id,status='queued',progress=0,stage='Queued after finding edit')
        db.add(queued); await db.flush()
    await write_audit(db,user,'finding.decision_recorded',{'finding_id':finding.id,'action':body.action,'reason':body.reason.strip(),'state':finding.state,'india_pack_codes':sorted(c for c in india_codes if c)})
    if queued: await write_audit(db,user,'claim_court.analysis_queued',{'content_id':item.id,'revision_id':queued.revision_id,'job_id':queued.id,'trigger':'finding_edit'})
    await db.commit(); await db.refresh(row)
    response={'id':row.id,'finding_id':row.finding_id,'action':row.action,'reason':row.reason,'user_id':row.user_id,'state':finding.state,'created_at':row.created_at.isoformat()}
    if queued:
        from app.api.content import _run_analysis_job
        background_tasks.add_task(_run_analysis_job,queued.id,item.id,user.workspace_id,user.id)
        response['new_revision_version']=item.current_revision; response['review_job_id']=queued.id; response['message']='Edited text saved as a new revision and Claim Court re-check queued.'
    return response

@router.get('/content/{content_id}/decisions')
async def list_decisions(content_id: str, user: CurrentUser, db: DBSession):
    await get_item(content_id,user,db)
    findings=(await db.scalars(select(ClaimFinding.id).where(ClaimFinding.content_id==content_id,ClaimFinding.workspace_id==user.workspace_id))).all()
    if not findings: return []
    rows=(await db.scalars(select(FindingDecision).where(FindingDecision.workspace_id==user.workspace_id,FindingDecision.finding_id.in_(findings)).order_by(FindingDecision.created_at))).all()
    return [{'id':x.id,'finding_id':x.finding_id,'action':x.action,'reason':x.reason,'user_id':x.user_id,'created_at':x.created_at.isoformat()} for x in rows]

@router.post('/content/{content_id}/workflow')
async def change_workflow(content_id: str, body: StateInput, user: CurrentUser, db: DBSession):
    item=await get_item(content_id,user,db); action=body.action
    if action=='submit':
        if user.role not in {'creator','manager','admin'}: raise HTTPException(403,'Only creators or managers can submit content.')
        if item.status not in {'draft','rejected','analyzed'}: raise HTTPException(409,f'Cannot submit from {item.status}.')
        item.status='submitted'
    elif action=='start_review':
        require_role(user,REVIEW_ROLES)
        if item.status!='submitted': raise HTTPException(409,'Only submitted content can enter review.')
        item.status='in_review'
    elif action=='approve':
        require_role(user,MANAGER_ROLES)
        if item.status=='approved': raise HTTPException(409,'This content is already approved and locked.')
        if item.status!='in_review': raise HTTPException(409,'Content must be in review before approval.')
        revision=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
        findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.workspace_id==user.workspace_id,ClaimFinding.revision_id==revision.id))).all() if revision else []
        unresolved=[]
        for finding in findings:
            if not is_approval_blocker(finding.verdict, finding.severity): continue
            latest_decision=await db.scalar(select(FindingDecision).where(FindingDecision.finding_id==finding.id,FindingDecision.workspace_id==user.workspace_id).order_by(desc(FindingDecision.created_at)).limit(1))
            if not latest_decision or not decision_clears_approval_block(latest_decision.action, finding.evidence or []):
                unresolved.append({'finding_id':finding.id,'verdict':finding.verdict,'severity':finding.severity,'required_action':'resolve or authorised override'})
        if unresolved: raise HTTPException(409, detail={'message':'Approval blocked: resolve or use an authorised override for each blocking finding on the current revision. Accept alone does not clear a blocking finding.','unresolved':unresolved})
        if not revision: raise HTTPException(409,'Current revision is missing.')
        snapshot_decisions=[]
        for f in findings:
            decision_rows=(await db.scalars(select(FindingDecision).where(FindingDecision.finding_id==f.id,FindingDecision.workspace_id==user.workspace_id).order_by(FindingDecision.created_at))).all()
            snapshot_decisions.extend({'finding_id':f.id,'action':d.action,'reason':d.reason,'user_id':d.user_id,'created_at':d.created_at.isoformat()} for d in decision_rows)
        snapshot = {
            'decisions': snapshot_decisions,
            'content': {'id':item.id,'title':item.title,'channel':item.channel,'campaign':item.campaign,'revision_version':revision.version},
            'revision': {'id':revision.id,'caption':revision.caption,'creative_filename':revision.creative_filename,'creative_storage_key':revision.creative_storage_key,'ocr_text':revision.ocr_text,'ocr_status':revision.ocr_status},
            'findings': [{'id':f.id,'claim_text':f.claim_text,'verdict':f.verdict,'severity':f.severity,'rationale':f.rationale,'evidence':f.evidence or []} for f in findings],
            'approved_at':datetime.now(timezone.utc).isoformat(),
            'approved_by':user.id,
        }
        revision.locked_at=datetime.now(timezone.utc); revision.approved_by=user.id; revision.approved_snapshot=snapshot
        item.status='approved'
    elif action=='reject':
        require_role(user,REVIEW_ROLES)
        if item.status not in {'submitted','in_review'}: raise HTTPException(409,'Only submitted or in-review content can be rejected.')
        if not body.reason.strip(): raise HTTPException(422,'A rejection reason is required.')
        item.status='rejected'
    elif action=='reopen':
        require_role(user,MANAGER_ROLES)
        if item.status!='approved': raise HTTPException(409,'Only approved content can be reopened.')
        # Reopening creates a brand new draft revision so the approved and locked revision remains immutable
        current=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
        next_ver = (current.version if current else 1) + 1
        new_rev = ContentRevision(
            workspace_id=user.workspace_id,
            content_id=item.id,
            version=next_ver,
            caption=current.caption if current else '',
            alt_text=current.alt_text if current else '',
            is_ai_media=current.is_ai_media if current else False,
            detected_language=current.detected_language if current else 'unknown',
            creative_filename=current.creative_filename if current else None,
            creative_storage_key=current.creative_storage_key if current else None,
            ocr_text=current.ocr_text if current else '',
            ocr_status=current.ocr_status if current else 'not_run',
            created_by=user.id,
        )
        db.add(new_rev); await db.flush()
        item.current_revision = new_rev.version
        item.status='draft'
    await write_audit(db,user,'content.workflow_changed',{'content_id':item.id,'action':action,'reason':body.reason.strip(),'status':item.status})
    await db.commit(); await db.refresh(item)
    return {'content_id':item.id,'status':item.status,'action':action,'locked_revision_id':revision.id if action=='approve' and revision else None}

@router.get('/content/{content_id}/export')
async def export_approved_content(content_id: str, user: CurrentUser, db: DBSession):
    item=await get_item(content_id,user,db)
    if item.status!='approved': raise HTTPException(409,'Export is locked until a manager approves the content.')
    rev=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not rev: raise HTTPException(409,'Current revision is missing.')
    if not rev.locked_at or not rev.approved_snapshot:
        raise HTTPException(409,'Approved revision snapshot is missing; re-approve after reviewing the current revision.')
    findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.workspace_id==user.workspace_id,ClaimFinding.revision_id==rev.id))).all()
    decisions=[]
    for f in findings:
        rows=(await db.scalars(select(FindingDecision).where(FindingDecision.finding_id==f.id,FindingDecision.workspace_id==user.workspace_id).order_by(FindingDecision.created_at))).all()
        decisions.extend({'finding_id':f.id,'action':d.action,'reason':d.reason,'user_id':d.user_id,'created_at':d.created_at.isoformat()} for d in rows)
    return {'product':'BrandCourt','content':rev.approved_snapshot.get('content', {'id':item.id,'title':item.title,'channel':item.channel,'campaign':item.campaign,'status':item.status}),'revision':rev.approved_snapshot.get('revision', {'version':rev.version,'caption':rev.caption,'creative_filename':rev.creative_filename,'ocr_status':rev.ocr_status}),'findings':rev.approved_snapshot.get('findings',[]),'decisions':rev.approved_snapshot.get('decisions',[]),'approved_snapshot':True,'approved_at':rev.locked_at.isoformat(),'exported_at':datetime.now(timezone.utc).isoformat(),'notice':'This export records the immutable approved snapshot and its review state; it is not legal advice.'}
