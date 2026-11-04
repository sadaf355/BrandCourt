"""R4/R5 release APIs: image intelligence, reviewer queue, reports and model disclosures."""
from datetime import datetime, timezone
from pathlib import Path
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, desc
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.models.entities import ContentItem, ContentRevision, ClaimFinding, Rule, BrandAsset, AICall, Report
from app.services.image_intelligence import analyze_image

router=APIRouter(tags=['image intelligence, reports and reviewer queue'])
REVIEW_ROLES={'reviewer','manager','admin'}
MANAGER_ROLES={'manager','admin'}

def _role(user, roles):
    if user.role not in roles: raise HTTPException(403,'Your workspace role does not permit this action.')

@router.get('/review-queue')
async def reviewer_queue(user: CurrentUser, db: DBSession):
    _role(user, REVIEW_ROLES)
    items=(await db.scalars(select(ContentItem).where(ContentItem.workspace_id==user.workspace_id,ContentItem.status.in_(['submitted','in_review'])).order_by(ContentItem.updated_at))).all()
    rows=[]
    for item in items:
        rev=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
        findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.revision_id==rev.id,ClaimFinding.workspace_id==user.workspace_id))).all() if rev else []
        rows.append({'id':item.id,'title':item.title,'channel':item.channel,'status':item.status,'current_revision':item.current_revision,'language':rev.detected_language if rev else 'unknown','finding_count':len(findings),'critical_count':sum(1 for f in findings if f.severity.lower() in {'critical','blocker'}),'updated_at':item.updated_at.isoformat()})
    return rows

@router.post('/content/{content_id}/image-analysis')
async def image_analysis(content_id: str, user: CurrentUser, db: DBSession):
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    rev=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not rev or not rev.creative_storage_key: raise HTTPException(409,'Attach an image creative before image analysis.')
    image_path=Path(settings.upload_dir)/rev.creative_storage_key
    if not image_path.exists(): raise HTTPException(404,'Stored creative file is missing.')
    palette=[]
    assets=(await db.scalars(select(BrandAsset).where(BrandAsset.workspace_id==user.workspace_id,BrandAsset.kind=='palette'))).all()
    for asset in assets:
        raw=asset.data or {}
        values=raw.get('colors',raw.get('palette',[]))
        if isinstance(values,dict): values=list(values.values())
        if isinstance(values,list): palette.extend(v for v in values if isinstance(v,str) and v.startswith('#'))
    logo_ref=None
    logo_assets=(await db.scalars(select(BrandAsset).where(BrandAsset.workspace_id==user.workspace_id,BrandAsset.kind=='logo'))).all()
    for asset in logo_assets:
        candidate=(asset.data or {}).get('reference_image_path')
        if candidate:
            p=(Path(settings.upload_dir)/str(candidate)).resolve()
            root=Path(settings.upload_dir).resolve()
            if root in p.parents and p.is_file(): logo_ref=p; break
    try:
        result=analyze_image(image_path,palette,logo_ref)
    except ImportError as exc:
        raise HTTPException(503,'Image analysis dependencies unavailable. Install Pillow and pytesseract and the Tesseract system engine.') from exc
    except Exception as exc:
        # Failed checks are explicitly routed to human review, never treated as a pass.
        result={'overall_status':'needs_human_review','error':type(exc).__name__,'message':'Image analysis failed; manual review is required.','ocr_boxes':[],'palette_checks':[],'contrast':{'status':'needs_human_review'},'logo_check':{'status':'needs_human_review'}}
    rev.image_analysis=result
    if result.get('ocr_text'):
        rev.ocr_text=result['ocr_text']; rev.ocr_status='completed'
    else:
        rev.ocr_status='failed' if 'error' in result else 'no_text_found'
    await write_audit(db,user,'creative.image_analysis',{'content_id':item.id,'revision_id':rev.id,'status':result.get('overall_status')})
    await db.commit()
    return {'content_id':item.id,'revision_id':rev.id,**result}

@router.get('/content/{content_id}/report')
async def content_report(content_id: str, user: CurrentUser, db: DBSession, format: str=Query(default='json',pattern='^(json|pdf)$')):
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    rev=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not rev: raise HTTPException(409,'Current revision missing.')
    findings=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.revision_id==rev.id,ClaimFinding.workspace_id==user.workspace_id).order_by(ClaimFinding.created_at))).all()
    calls=(await db.scalars(select(AICall).where(AICall.workspace_id==user.workspace_id,AICall.revision_id==rev.id).order_by(AICall.started_at))).all()
    payload={'product':'BrandCourt','report_version':'1.0','generated_at':datetime.now(timezone.utc).isoformat(),'content':{'id':item.id,'title':item.title,'channel':item.channel,'campaign':item.campaign,'status':item.status},'revision':{'id':rev.id,'version':rev.version,'caption':rev.caption,'alt_text':rev.alt_text,'is_ai_media':rev.is_ai_media,'language':rev.detected_language,'ocr_status':rev.ocr_status},'findings':[{'id':f.id,'claim_text':f.claim_text,'verdict':f.verdict,'severity':f.severity,'rationale':f.rationale,'evidence':f.evidence or [],'analysis_method':f.analysis_method} for f in findings],'ai_and_service_disclosure':{'calls':[{'provider':c.provider,'model':c.model,'purpose':c.purpose,'input_chars_after_masking':c.input_chars,'masked_entities':c.masked_entities,'status':c.status,'duration_ms':c.duration_ms} for c in calls],'external_ai_called':any(c.provider not in {'deterministic','local'} for c in calls),'notice':'The current baseline is deterministic. Sensitive patterns are masked before any optional provider call. Verify deployment configuration before sending data to an external service.'},'limitations':['Language detection is heuristic, especially for Hindi/Marathi/Hinglish.','Image checks may route to human review when evidence is unavailable.','Findings are advisory and not legal advice.']}
    db.add(Report(workspace_id=user.workspace_id,revision_id=rev.id,json_summary=payload,created_by=user.id))
    await write_audit(db,user,'report.generated',{'content_id':item.id,'revision_id':rev.id,'format':format})
    await db.commit()
    if format=='json':
        return payload
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from io import BytesIO
        buffer=BytesIO(); doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
        styles=getSampleStyleSheet(); story=[Paragraph('BrandCourt Review Report',styles['Title']),Paragraph(item.title,styles['Heading1']),Paragraph(f"Channel: {item.channel} | Status: {item.status} | Revision: v{rev.version}",styles['Normal']),Spacer(1,12),Paragraph('Content',styles['Heading2']),Paragraph((rev.caption or '(empty)').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>'),styles['BodyText']),Spacer(1,12),Paragraph('Findings',styles['Heading2'])]
        if not findings: story.append(Paragraph('No findings recorded for this revision.',styles['BodyText']))
        for f in findings:
            story.extend([Paragraph(f"{f.verdict.upper()} · {f.severity.upper()}",styles['Heading3']),Paragraph(f.claim_text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),styles['BodyText']),Paragraph(f.rationale.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),styles['BodyText']),Spacer(1,6)])
        story.extend([Spacer(1,10),Paragraph('AI / service disclosure',styles['Heading2']),Paragraph(f"External AI called: {payload['ai_and_service_disclosure']['external_ai_called']}. Calls recorded: {len(calls)}. Current mode: deterministic baseline. Sensitive-pattern masking and provider disclosure should be verified in the deployed environment.",styles['BodyText']),Spacer(1,8),Paragraph('Limitations: heuristic language detection; image checks may require human review; this report is not legal advice.',styles['Italic'])])
        doc.build(story)
        return Response(buffer.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="brandcourt-{item.id[:8]}-v{rev.version}.pdf"'})
    except ImportError as exc:
        raise HTTPException(503,'PDF export requires reportlab. Install backend requirements and retry.') from exc

@router.get('/model-calls')
async def model_calls(user: CurrentUser, db: DBSession, limit: int=Query(default=100,ge=1,le=500)):
    rows=(await db.scalars(select(AICall).where(AICall.workspace_id==user.workspace_id).order_by(desc(AICall.started_at)).limit(limit))).all()
    return [{'id':r.id,'revision_id':r.revision_id,'provider':r.provider,'model':r.model,'purpose':r.purpose,'input_chars':r.input_chars,'masked_entities':r.masked_entities,'started_at':r.started_at.isoformat(),'duration_ms':r.duration_ms,'status':r.status} for r in rows]


@router.get('/model-mode')
async def model_mode(user: CurrentUser):
    mode=settings.model_mode.lower()
    return {'mode':mode if mode in {'deterministic','ollama'} else 'deterministic','provider':'ollama' if mode=='ollama' else 'deterministic','model':settings.ollama_model if mode=='ollama' else 'deterministic_baseline','base_url_configured':bool(settings.ollama_base_url),'notice':'Ollama calls use masked claim/evidence text. If local inference fails or returns invalid output, the result is Needs human review.'}
