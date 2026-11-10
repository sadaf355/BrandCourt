from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import asyncio
import re
import hashlib
import json
import time
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, update
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.core.job_queue import enqueue_review_job
from app.core.rate_limit import enforce_analyze_rate_limit
from app.core.storage import get_storage
from app.models.entities import ContentItem, ContentRevision, ClaimFinding, Fact, Rule, Precedent, ReviewJob, User, BrandAsset, Embedding, AICall, CheckCache, RuleExample, Workspace, normalize_severity
from app.services.claim_policy import _normalized_number_comparison, _claim_builtin_policy, compare_claim_to_fact, fact_outside_validity_window, is_risky_claim
from app.services.text_intelligence import mask_sensitive, mask_sensitive_with_map, MaskingFailure, detect_language, layer1_checks, advisory_tone
from app.services.semantic_retrieval import (
    embedding,
    embedding_provider_for,
    hybrid_similarity,
    ollama_nli,
    cosine,
)
from app.services.checking_engine import extract_claims_regex, reciprocal_rank_fusion, optional_rerank, merge_overlapping_spans
from app.services.model_provider import (
    Adjudication, ClaimExtraction, ModelStepFailed, configured_provider, validated_json,
    verify_adjudication_quote,
)
from app.services.image_upload import reencode_image
from app.services.precedents import matching_approved_precedents

router = APIRouter(tags=['content review and Claim Court'])
EDIT_ROLES = {'creator', 'admin', 'manager'}
ANALYZE_ROLES = {'creator', 'reviewer', 'manager', 'admin'}
EVALUATION_REQUEST_LIMIT = 40

def role_check(user, roles):
    if user.role not in roles:
        raise HTTPException(403, 'Your workspace role does not permit this action.')

def item_view(x):
    return {'id':x.id,'title':x.title,'channel':x.channel,'campaign':x.campaign,'status':x.status,'current_revision':x.current_revision,'created_by':x.created_by,'created_at':x.created_at,'updated_at':x.updated_at}
def revision_view(x):
    return {'id':x.id,'content_id':x.content_id,'version':x.version,'caption':x.caption,'creative_filename':x.creative_filename,'ocr_status':getattr(x,'ocr_status','not_run'),'ocr_text':getattr(x,'ocr_text',''),'alt_text':getattr(x,'alt_text',''),'is_ai_media':getattr(x,'is_ai_media',False),'paid_gifted':x.paid_gifted,'detected_language':getattr(x,'detected_language','unknown'),'image_analysis':getattr(x,'image_analysis',None),'created_by':x.created_by,'created_at':x.created_at}
def finding_view(x):
    return {'id':x.id,'content_id':x.content_id,'revision_id':x.revision_id,'claim_text':x.claim_text,'verdict':x.verdict,'rationale':x.rationale,'evidence':x.evidence or [],'severity':x.severity,'layer':x.layer,'span_start':x.span_start,'span_end':x.span_end,'region':x.region,'suggested_fix':x.suggested_fix,'intent_preserved':({'purpose':'Original communication intent','cta':'Preserved' if (x.intent_check or {}).get('call_to_action_present') else 'Not verified','claims_changed':list((x.intent_check or {}).get('changed_claims') or []),'safe':bool((x.intent_check or {}).get('intent_preserved')),'embedding_similarity':(x.intent_check or {}).get('embedding_similarity')} if x.intent_check else None),'analysis_method':x.analysis_method,'state':getattr(x,'state','open'),'created_at':x.created_at}

def _analyze_stored_image(
    storage,
    image_key: str,
    palette: list[str],
    logo_key: str | None,
    original_key: str | None,
):
    from app.services.image_intelligence import analyze_image

    with storage.materialize(image_key) as image_path:
        if logo_key and original_key:
            with storage.materialize(logo_key) as logo_path, storage.materialize(original_key) as original_path:
                return analyze_image(image_path, palette, logo_path, c2pa_path=original_path)
        if logo_key:
            with storage.materialize(logo_key) as logo_path:
                if original_key:
                    with storage.materialize(original_key) as original_path:
                        return analyze_image(image_path, palette, logo_path, c2pa_path=original_path)
                return analyze_image(image_path, palette, logo_path)
        if original_key:
            with storage.materialize(original_key) as original_path:
                return analyze_image(image_path, palette, c2pa_path=original_path)
        return analyze_image(image_path, palette)


class ContentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    channel: str = Field(pattern='^(website|instagram|facebook|linkedin|email|paid_ad|packaging|other)$')
    campaign: str = Field(default='', max_length=200)
    caption: str = Field(default='', max_length=30000)
    alt_text: str = Field(default='', max_length=3000)
    is_ai_media: bool = False
    paid_gifted: bool = False
class ContentEdit(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    channel: str | None = Field(default=None, pattern='^(website|instagram|facebook|linkedin|email|paid_ad|packaging|other)$')
    campaign: str | None = Field(default=None, max_length=200)
    caption: str | None = Field(default=None, max_length=30000)
    alt_text: str | None = Field(default=None, max_length=3000)
    is_ai_media: bool | None = None
    paid_gifted: bool | None = None

@router.get('/content')
async def list_content(user: CurrentUser, db: DBSession):
    rows = (await db.scalars(select(ContentItem).where(ContentItem.workspace_id==user.workspace_id).order_by(desc(ContentItem.updated_at)))).all()
    return [item_view(x) for x in rows]

@router.post('/content', status_code=201)
async def create_content(body: ContentCreate, user: CurrentUser, db: DBSession):
    role_check(user, EDIT_ROLES)
    item = ContentItem(workspace_id=user.workspace_id,title=body.title.strip(),channel=body.channel,campaign=body.campaign.strip(),status='draft',current_revision=1,created_by=user.id)
    db.add(item); await db.flush()
    revision = ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=1,caption=body.caption,alt_text=body.alt_text,is_ai_media=body.is_ai_media,paid_gifted=body.paid_gifted,detected_language=detect_language(body.caption)['language'],created_by=user.id)
    db.add(revision); await db.flush()
    await write_audit(db,user,'content.created',{'content_id':item.id,'revision_id':revision.id,'version':1})
    await db.commit(); await db.refresh(item)
    return {**item_view(item),'revision':revision_view(revision)}

@router.get('/content/{content_id}')
async def get_content(content_id: str, user: CurrentUser, db: DBSession):
    item = await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    revisions = (await db.scalars(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)))).all()
    findings = (await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.workspace_id==user.workspace_id,ClaimFinding.revision_id==revisions[0].id).order_by(ClaimFinding.created_at))).all() if revisions else []
    return {**item_view(item),'revisions':[revision_view(x) for x in revisions],'findings':[finding_view(x) for x in findings]}

@router.post('/content/{content_id}/revisions', status_code=201)
async def create_revision(content_id: str, body: ContentEdit, user: CurrentUser, db: DBSession):
    role_check(user, EDIT_ROLES)
    item = await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    latest_locked = await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision,ContentRevision.locked_at.is_not(None)))
    if latest_locked and item.status == 'approved': raise HTTPException(409,'Approved revision is locked. Reopen the item before creating a new revision.')
    changes = body.model_dump(exclude_unset=True)
    if 'title' in changes and changes['title'] is not None: item.title=changes['title'].strip()
    if 'channel' in changes and changes['channel'] is not None: item.channel=changes['channel']
    if 'campaign' in changes and changes['campaign'] is not None: item.campaign=changes['campaign'].strip()
    latest = await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)))
    version = (latest.version if latest else 0)+1
    caption = changes.get('caption') if changes.get('caption') is not None else (latest.caption if latest else '')
    alt_text = changes.get('alt_text') if changes.get('alt_text') is not None else (latest.alt_text if latest else '')
    is_ai_media = changes.get('is_ai_media') if changes.get('is_ai_media') is not None else (latest.is_ai_media if latest else False)
    paid_gifted = changes.get('paid_gifted')
    if paid_gifted is None:
        paid_gifted = latest.paid_gifted if latest else False
    revision = ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=version,caption=caption,alt_text=alt_text,is_ai_media=is_ai_media,paid_gifted=paid_gifted,detected_language=detect_language(caption)['language'],creative_filename=latest.creative_filename if latest else None,creative_storage_key=latest.creative_storage_key if latest else None,image_analysis=latest.image_analysis if latest else None,ocr_text=latest.ocr_text if latest else '',ocr_status=latest.ocr_status if latest else 'not_run',created_by=user.id)
    item.current_revision=version; item.status='draft'
    db.add(revision); await db.flush()
    await write_audit(db,user,'content.revision_created',{'content_id':item.id,'revision_id':revision.id,'version':version})
    await db.commit(); await db.refresh(item); await db.refresh(revision)
    return {**item_view(item),'revision':revision_view(revision)}

@router.get('/content/{content_id}/revisions')
async def list_revisions(content_id: str, user: CurrentUser, db: DBSession):
    if not await db.scalar(select(ContentItem.id).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id)):
        raise HTTPException(404,'Content item not found.')
    rows=(await db.scalars(select(ContentRevision).where(ContentRevision.content_id==content_id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)))).all()
    return [revision_view(x) for x in rows]

@router.post('/content/{content_id}/creative', status_code=201)
async def upload_creative(content_id: str, user: CurrentUser, db: DBSession, file: UploadFile = File(...)):
    role_check(user, EDIT_ROLES)
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    locked = await db.scalar(select(ContentRevision.id).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision,ContentRevision.locked_at.is_not(None)))
    if locked: raise HTTPException(409,'This revision is locked. Reopen the item and create a new revision before attaching or replacing its creative.')
    filename=Path(file.filename or 'creative').name
    suffix=Path(filename).suffix.lower()
    if suffix not in {'.png','.jpg','.jpeg','.webp','.gif'}: raise HTTPException(415,'Supported creative formats: PNG, JPG, WEBP and GIF.')
    raw=await file.read(10 * 1024 * 1024 + 1)
    if not raw: raise HTTPException(400,'Creative must not be empty.')
    if len(raw)>10*1024*1024: raise HTTPException(413,'Creative must be no larger than 10 MB.')
    try:
        processed, thumbnail, width, height = reencode_image(raw, suffix)
    except OverflowError as exc:
        raise HTTPException(413, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    latest=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)))
    if not latest: raise HTTPException(409,'Create a content revision before uploading a creative.')
    upload_id = uuid4().hex
    key=f'{user.workspace_id}/creatives/{upload_id}.webp'
    original_key=f'{user.workspace_id}/creatives/{upload_id}.original{suffix}'
    thumbnail_key=f'{user.workspace_id}/creatives/{upload_id}.thumbnail.webp'
    original_content_type = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.webp': 'image/webp', '.gif': 'image/gif',
    }[suffix]
    try:
        storage = get_storage()
        await asyncio.to_thread(storage.put_bytes, original_key, raw, original_content_type)
        await asyncio.to_thread(storage.put_bytes, key, processed, 'image/webp')
        await asyncio.to_thread(storage.put_bytes, thumbnail_key, thumbnail, 'image/webp')
    except Exception as exc:
        raise HTTPException(503, 'Creative storage is unavailable.') from exc
    latest.creative_filename=filename
    latest.creative_storage_key=key
    latest.ocr_text=''
    latest.ocr_status='not_run'
    latest.image_analysis={
        'upload': {
            'original_storage_key': original_key,
            'thumbnail_storage_key': thumbnail_key,
            'processed_storage_key': key,
            'width': width,
            'height': height,
        }
    }
    await write_audit(db,user,'content.creative_uploaded',{'content_id':item.id,'revision_id':latest.id,'filename':filename})
    await db.commit(); await db.refresh(latest)
    return revision_view(latest)

async def _perform_analysis(db, user, item, revision, job=None):
    evaluation_variant = None
    if job and isinstance(job.result, dict):
        evaluation_variant = job.result.get("_evaluation_variant")
    if evaluation_variant not in {
        None, "code_rules_only", "retrieval_and_nli", "full_pipeline",
    }:
        raise RuntimeError("The review job contains an unsupported evaluation variant.")
    run_visual_checks = evaluation_variant in {None, "full_pipeline"}
    run_claim_checks = evaluation_variant != "code_rules_only"

    async def progress(value, stage):
        if job:
            if not job.lease_owner:
                raise RuntimeError("Analysis job has no active worker lease.")
            result = await db.execute(
                update(ReviewJob)
                .where(
                    ReviewJob.id == job.id,
                    ReviewJob.workspace_id == job.workspace_id,
                    ReviewJob.status == "running",
                    ReviewJob.lease_owner == job.lease_owner,
                )
                .values(progress=value, stage=stage)
            )
            if result.rowcount != 1:
                raise RuntimeError("Analysis worker lease was lost.")
            await db.commit()
    await progress(5, 'image_analysis' if run_visual_checks else 'visual_checks_skipped')
    old=(await db.scalars(select(ClaimFinding).where(ClaimFinding.revision_id==revision.id,ClaimFinding.workspace_id==user.workspace_id))).all()
    for finding in old: await db.delete(finding)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    workspace_settings = workspace.settings if workspace else {}
    upload_info = (revision.image_analysis or {}).get('upload')
    if revision.creative_storage_key and run_visual_checks:
        palette_asset = await db.scalar(
            select(BrandAsset)
            .where(BrandAsset.workspace_id == user.workspace_id, BrandAsset.kind == 'palette')
            .order_by(BrandAsset.updated_at.desc())
        )
        palette_data = (palette_asset.data or {}) if palette_asset else {}
        palette = palette_data.get('colors', [])
        if isinstance(palette, str):
            palette = re.split(r'[,;\n]', palette)
        if not isinstance(palette, list):
            palette = []
        palette = [color for color in palette if isinstance(color, str)]
        logo_asset = await db.scalar(
            select(BrandAsset)
            .where(BrandAsset.workspace_id == user.workspace_id, BrandAsset.kind == 'logo')
            .order_by(BrandAsset.updated_at.desc())
        )
        logo_data = (logo_asset.data or {}) if logo_asset else {}
        logo_key = logo_data.get('storage_key') if isinstance(logo_data, dict) else None
        try:
            # analyze_image performs Tesseract OCR and OpenCV work synchronously;
            # keep the entire image pipeline off the event loop.
            image_result = await asyncio.to_thread(
                _analyze_stored_image, get_storage(), revision.creative_storage_key, palette,
                logo_key if isinstance(logo_key, str) else None,
                upload_info.get('original_storage_key') if isinstance(upload_info, dict) else None,
            )
            if not palette:
                image_result['findings'].append({
                    'code': 'brand_palette_unconfigured',
                    'status': 'needs_human_review',
                    'severity': 'advisory',
                    'region': {'x': 0, 'y': 0, 'width': image_result['width'], 'height': image_result['height'],
                               'image_width': image_result['width'], 'image_height': image_result['height']},
                    'message': 'No brand palette is configured; color compliance could not be compared.',
                    'analysis_method': 'image_palette_unavailable',
                })
            revision.ocr_text = image_result['ocr_text']
            revision.ocr_status = image_result['ocr_status']
        except Exception as exc:
            image_result = {
                'overall_status': 'needs_human_review',
                'ocr_text': '',
                'ocr_status': 'failed',
                'width': upload_info.get('width') if isinstance(upload_info, dict) else None,
                'height': upload_info.get('height') if isinstance(upload_info, dict) else None,
                'ocr_message': f'Image analysis failed ({type(exc).__name__}); human review is required.',
                'findings': [{
                    'code': 'image_analysis_failed',
                    'status': 'needs_human_review',
                    'severity': 'major',
                    'region': None,
                    'message': f'Image analysis failed ({type(exc).__name__}); no visual check is treated as a pass.',
                    'analysis_method': 'image_analysis_failure',
                }],
            }
            revision.ocr_text = ''
            revision.ocr_status = 'failed'
        if upload_info:
            image_result['upload'] = upload_info
        image_width = image_result.get('width')
        image_height = image_result.get('height')
        if image_width and image_height:
            for visual in image_result.get('findings', []):
                if not visual.get('region'):
                    visual['region'] = {
                        'x': 0, 'y': 0, 'width': image_width, 'height': image_height,
                        'image_width': image_width, 'image_height': image_height,
                    }
        revision.image_analysis = image_result
    await progress(15, 'masking')
    claim_ocr_text = (
        (revision.image_analysis or {}).get('ocr_claim_text', revision.ocr_text or '')
        if run_visual_checks else ''
    )
    text='\n'.join(part for part in [revision.caption.strip(), claim_ocr_text.strip()] if part)
    language_info=detect_language(text)
    revision.detected_language=language_info['language']
    model_mode = str(
        "disabled" if evaluation_variant == "code_rules_only"
        else "ollama" if evaluation_variant in {"retrieval_and_nli", "full_pipeline"}
        else workspace_settings.get("model_mode") or settings.model_mode
    ).lower()
    secret_terms = workspace_settings.get("secret_terms", [])
    if not isinstance(secret_terms, list):
        secret_terms = []
    masking_failed = False
    masking_failure = None
    try:
        masked_text, masked_count, local_mask_map = mask_sensitive_with_map(text, secret_terms)
    except MaskingFailure:
        masked_text, masked_count, local_mask_map = "", 0, {}
        masking_failed = True
        masking_failure = ClaimFinding(
            workspace_id=user.workspace_id, content_id=item.id, revision_id=revision.id,
            claim_text="[privacy masking failed]", verdict="needs_human_review",
            rationale="Sensitive-data masking failed; no model call was made. Human review is required.",
            evidence=[{"type": "failed_step", "stage": "masking"}], severity="major",
            layer="masking", analysis_method="privacy_failure",
        )
    facts=(
        (await db.scalars(select(Fact).where(
            Fact.workspace_id==user.workspace_id, Fact.status=='active'
        ))).all()
        if run_claim_checks else []
    )
    rules=(await db.scalars(select(Rule).where(Rule.workspace_id==user.workspace_id,Rule.status=='active'))).all()
    now=datetime.now(timezone.utc); outputs=[]
    image_result = revision.image_analysis or {} if run_visual_checks else {}
    for visual in image_result.get('findings', []):
        if visual.get('code') in {'ocr_unavailable', 'ocr_no_text'}:
            continue
        is_uncertain_ocr = visual.get('analysis_method') == 'ocr_confidence'
        finding = ClaimFinding(
            workspace_id=user.workspace_id, content_id=item.id, revision_id=revision.id,
            claim_text=(
                f"[uncertain OCR: {visual.get('message', 'word needs verification')}]"
                if is_uncertain_ocr
                else f"[visual: {visual.get('code', 'image check')}]"
            ),
            verdict='needs_human_review', rationale=visual.get('message', 'Visual verification requires human review.'),
            evidence=[{
                'type': 'visual_check', 'code': visual.get('code'),
                'analysis_method': visual.get('analysis_method'), 'region': visual.get('region'),
            }],
            severity=visual.get('severity', 'major'),
            layer='ocr' if is_uncertain_ocr else 'visual',
            region=visual.get('region'),
            analysis_method=visual.get('analysis_method', 'image_heuristic'),
        )
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    if masking_failure:
        db.add(masking_failure); await db.flush(); outputs.append(finding_view(masking_failure))

    async def mask_model_input(source):
        nonlocal masking_failed
        if masking_failed:
            return "", 0, {}
        try:
            return mask_sensitive_with_map(source, secret_terms)
        except MaskingFailure:
            masking_failed = True
            failure = ClaimFinding(
                workspace_id=user.workspace_id, content_id=item.id, revision_id=revision.id,
                claim_text="[privacy masking failed]", verdict="needs_human_review",
                rationale="Sensitive-data masking failed; no further model call was made. Human review is required.",
                evidence=[{"type": "failed_step", "stage": "masking"}],
                severity="major", layer="masking", analysis_method="privacy_failure",
            )
            db.add(failure); await db.flush(); outputs.append(finding_view(failure))
            return "", 0, {}

    if run_visual_checks and revision.creative_storage_key and revision.ocr_status in {
        "no_text_found", "failed", "unavailable", "unsupported_vector",
    }:
        image_result = revision.image_analysis or {}
        dimensions = {
            "image_width": image_result.get("width"),
            "image_height": image_result.get("height"),
        }
        ocr_region = (
            {"x": 0, "y": 0, "width": dimensions["image_width"], "height": dimensions["image_height"], **dimensions}
            if dimensions["image_width"] and dimensions["image_height"] else None
        )
        ocr_failure = ClaimFinding(
            workspace_id=user.workspace_id, content_id=item.id, revision_id=revision.id,
            claim_text="[creative OCR returned no usable text]",
            verdict="needs_human_review",
            rationale=(image_result.get('ocr_message') or "OCR did not produce usable text for the uploaded creative. Caption checks continue, but the image text must be reviewed manually."),
            evidence=[{"type": "failed_step", "stage": "ocr", "status": revision.ocr_status}],
            severity="major", layer="ocr", region=ocr_region, analysis_method="ocr_failure",
        )
        db.add(ocr_failure); await db.flush(); outputs.append(finding_view(ocr_failure))
    claim_records = extract_claims_regex(text) if run_claim_checks else []
    model_extraction_failed = False
    provider = (
        configured_provider(settings, model_mode)
        if model_mode not in {"disabled", "deterministic", "off"}
        else None
    )
    if (
        not masking_failed
        and model_mode not in {"disabled", "deterministic", "off"}
        and evaluation_variant != "retrieval_and_nli"
    ):
        try:
            if provider.name != "disabled":
                rule_version = hashlib.sha256(
                    "|".join(f"{rule.code}:{rule.version}" for rule in sorted(rules, key=lambda rule: rule.code)).encode()
                ).hexdigest()
                cache_key = hashlib.sha256(
                    f"{user.workspace_id}:claims:{provider.name}:{provider.model}:{rule_version}:{masked_text}".encode()
                ).hexdigest()
                cache = await db.scalar(select(CheckCache).where(
                    CheckCache.key == cache_key, CheckCache.workspace_id == user.workspace_id
                ))
                if cache:
                    extracted = ClaimExtraction.model_validate(cache.result_json)
                else:
                    call_rows = {}
                    started_at = {}

                    async def log_extraction_call(status, attempt):
                        if status == "started":
                            started_at[attempt] = time.perf_counter()
                            row = AICall(
                                workspace_id=user.workspace_id, revision_id=revision.id,
                                provider=provider.name, model=provider.model,
                                purpose="claim_extraction", input_chars=len(masked_text),
                                masked_entities=masked_count, status="started",
                            )
                            db.add(row); call_rows[attempt] = row
                            await db.flush()
                        elif attempt in call_rows:
                            call_rows[attempt].status = status
                            call_rows[attempt].duration_ms = int(
                                (time.perf_counter() - started_at[attempt]) * 1000
                            )

                    extracted = await validated_json(
                        provider,
                        system_prompt="Extract only claims stated in the supplied text. Return JSON matching the schema.",
                        user_prompt=masked_text[:12000],
                        output_model=ClaimExtraction,
                        on_call=log_extraction_call,
                    )
                    db.add(CheckCache(
                        key=cache_key, workspace_id=user.workspace_id,
                        result_json=extracted.model_dump(),
                    ))
                for candidate in extracted.claims:
                    restored = candidate.claim
                    for token, original in local_mask_map.items():
                        restored = restored.replace(token, original)
                    start = text.find(restored)
                    if start >= 0 and not any(existing["claim"] == restored for existing in claim_records):
                        claim_records.append({
                            "claim": restored, "span_start": start, "span_end": start + len(restored),
                        })
        except (ModelStepFailed, ValueError, KeyError):
            model_extraction_failed = True
    claims=[record["claim"] for record in claim_records]
    claim_vectors: dict[int, list[float]] = {}
    fact_vectors: dict[str, list[float]] = {}
    # Optional local semantic embeddings. Every input is masked before it leaves this process.
    # If the local embedding service is down, keep deterministic retrieval but make the failure visible.
    if not masking_failed and model_mode == 'ollama' and claims and facts:
        embedding_provider = embedding_provider_for(
            model_mode,
            settings.ollama_base_url,
            settings.ollama_embedding_model,
        )
        embedding_inputs=[]; embedding_mask_count=0
        for source in [*claims[:100], *[(f.statement+' '+str(f.value)+' '+(f.unit or '')).strip() for f in facts]]:
            masked_source, count, _local_map=await mask_model_input(source)
            if masking_failed:
                break
            embedding_inputs.append(masked_source[:3000]); embedding_mask_count += count
        embedded = {"status": "skipped"}
        if not masking_failed:
            started=time.perf_counter()
            embedded=await embedding_provider.embed(embedding_inputs)
            db.add(AICall(workspace_id=user.workspace_id,revision_id=revision.id,provider=embedding_provider.name,model=embedding_provider.model,purpose='claim_retrieval_embeddings',input_chars=sum(map(len,embedding_inputs)),masked_entities=embedding_mask_count,duration_ms=int((time.perf_counter()-started)*1000),status=embedded.get('status','needs_human_review')))
        if embedded.get('status') == 'completed':
            vectors=embedded['embeddings']; claim_count=min(len(claims),100)
            claim_vectors={i:vectors[i] for i in range(claim_count)}
            for fact_index,fact in enumerate(facts):
                vector=vectors[claim_count+fact_index]
                fact_vectors[fact.id]=vector
                model_key=f'{embedding_provider.name}:{embedding_provider.model}'
                existing_embedding=await db.scalar(select(Embedding.id).where(Embedding.workspace_id==user.workspace_id,Embedding.entity_type=='fact',Embedding.entity_id==fact.id,Embedding.model==model_key))
                if existing_embedding:
                    stored=await db.scalar(select(Embedding).where(Embedding.id==existing_embedding))
                    if stored: stored.vector_json=vector
                elif embedded.get('status') != 'skipped':
                    db.add(Embedding(workspace_id=user.workspace_id,entity_type='fact',entity_id=fact.id,model=model_key,vector_json=vector))
        else:
            message='Local embedding service is unavailable; deterministic retrieval is continuing, but semantic matching needs human review.'
            finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text='[semantic retrieval status]',verdict='needs_human_review',rationale=message,evidence=[{'type':'model_service','code':'LOCAL-EMBEDDING-UNAVAILABLE','text':embedded.get('reason',message),'source_ref':'Local Ollama embedding service'}],severity='major',analysis_method='model_service_fallback')
            db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    # Persist deterministic hashing vectors for fallback retrieval and reproducible auditability.
    for entity_type, entities in [('fact', facts), ('rule', rules)]:
        for entity in entities:
            exists=await db.scalar(select(Embedding.id).where(Embedding.workspace_id==user.workspace_id,Embedding.entity_type==entity_type,Embedding.entity_id==entity.id,Embedding.model=='hashing-trigram-v1'))
            if not exists:
                source=(getattr(entity,'statement','')+' '+getattr(entity,'value','')+' '+getattr(entity,'text','')+' '+getattr(entity,'title','')).strip()
                db.add(Embedding(workspace_id=user.workspace_id,entity_type=entity_type,entity_id=entity.id,model='hashing-trigram-v1',vector_json=embedding(source)))
    await progress(30, 'rules')
    india_pack_enabled = workspace_settings.get("india_pack_enabled", True) is not False
    active_rules = [
        rule for rule in rules
        if india_pack_enabled or not str(rule.code).upper().startswith("IN-")
    ]
    for check in layer1_checks(
        text, item.channel,
        revision.alt_text if revision.creative_storage_key else 'not applicable',
        revision.is_ai_media,
        paid_gifted=revision.paid_gifted,
        c2pa_data=(revision.image_analysis or {}).get("c2pa"),
        india_pack_enabled=india_pack_enabled,
        rules=active_rules,
    ):
        evidence=[{'type':'policy_pack','code':check['code'],'title':check['type'],'text':check['message'],'source_ref':check.get('source_note') or ('BrandCourt India starter guidance (not legal advice)' if str(check['code']).startswith('IN-') else 'Workspace guideline')}]
        image_analysis = revision.image_analysis or {}
        alt_region = None
        if check.get('code') == 'A11Y-ALT' and image_analysis.get('width') and image_analysis.get('height'):
            alt_region = {
                'x': 0, 'y': 0, 'width': image_analysis['width'], 'height': image_analysis['height'],
                'image_width': image_analysis['width'], 'image_height': image_analysis['height'],
            }
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text=text[:1000] or '[creative metadata]',verdict=check['verdict'],rationale=check['message'],evidence=evidence,severity=check['severity'],layer='rules',span_start=check.get('span_start'),span_end=check.get('span_end'),region=alt_region,suggested_fix=check.get('suggested_fix'),analysis_method='layer1_deterministic')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    await progress(55, 'claims')
    if model_extraction_failed:
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text='[claim extraction failed]',verdict='needs_human_review',rationale='Optional model claim extraction failed schema validation or was unavailable. Regex extraction continued; human review is required.',evidence=[{'type':'failed_step','stage':'claims'}],severity='major',layer='claims',analysis_method='model_step_failure')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    image_result=revision.image_analysis or {}
    precedents=(await db.scalars(select(Precedent).where(Precedent.workspace_id==user.workspace_id,Precedent.status=='approved',(Precedent.valid_to.is_(None) | (Precedent.valid_to >= now)),(Precedent.channel=='all') | (Precedent.channel==item.channel)))).all()
    for idx, claim in enumerate(claims[:100]):
        words=set(re.findall(r'[a-z0-9]+',claim.lower()))
        risky_claim = is_risky_claim(claim)
        evidence=[]; verdict='unsupported' if risky_claim else None
        rationale='No matching approved fact was found. This is unsupported for review, not a finding that the claim is false.' if risky_claim else ''
        severity='major' if risky_claim else 'advisory'
        scored=[]
        documents = [
            (fact.id, f"{fact.statement} {fact.value} {fact.unit or ''}")
            for fact in facts
        ]
        document_term_frequency: dict[str, int] = {}
        for _, document in documents:
            for term in set(re.findall(r"[a-z0-9]+", document.lower())):
                document_term_frequency[term] = document_term_frequency.get(term, 0) + 1
        rrf_top8 = reciprocal_rank_fusion(
            claim,
            documents,
            top_k=8,
            query_vector=claim_vectors.get(idx),
            document_vectors=fact_vectors,
        )
        ranked_ids = {identifier for _, identifier in rrf_top8}
        rerank_scores = {}
        if os.environ.get("RERANKER_URL", "").strip() and not masking_failed and rrf_top8:
            masked_query, query_mask_count, _ = await mask_model_input(claim)
            top_documents = [(identifier, dict(documents)[identifier]) for _, identifier in rrf_top8]
            masked_documents = []
            document_mask_count = 0
            for identifier, document_text in top_documents:
                masked_document, count, _ = await mask_model_input(document_text)
                if masking_failed:
                    break
                masked_documents.append((identifier, masked_document))
                document_mask_count += count
            if not masking_failed:
                rerank_started = time.perf_counter()
                try:
                    reranked = await optional_rerank(masked_query, masked_documents)
                    if reranked is not None:
                        rerank_scores = {identifier: score for score, identifier in reranked}
                    db.add(AICall(
                        workspace_id=user.workspace_id, revision_id=revision.id,
                        provider="reranker", model="configured-reranker",
                        purpose="fact_retrieval_reranking",
                        input_chars=len(masked_query)+sum(len(value) for _, value in masked_documents),
                        masked_entities=query_mask_count+document_mask_count,
                        duration_ms=int((time.perf_counter()-rerank_started)*1000),
                        status="completed",
                    ))
                except ModelStepFailed:
                    db.add(AICall(
                        workspace_id=user.workspace_id, revision_id=revision.id,
                        provider="reranker", model="configured-reranker",
                        purpose="fact_retrieval_reranking",
                        input_chars=len(masked_query)+sum(len(value) for _, value in masked_documents),
                        masked_entities=query_mask_count+document_mask_count,
                        duration_ms=int((time.perf_counter()-rerank_started)*1000),
                        status="failed",
                    ))
                    failure=ClaimFinding(
                        workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,
                        claim_text='[retrieval reranker unavailable]',verdict='needs_human_review',
                        rationale='The configured reranker failed; deterministic retrieval continued and a reviewer must confirm the fact match.',
                        evidence=[{'type':'failed_step','stage':'claims','service':'reranker'}],
                        severity='major',layer='claims',analysis_method='model_service_failure',
                    )
                    db.add(failure); await db.flush(); outputs.append(finding_view(failure))
        for fact in facts:
            if fact.id not in ranked_ids:
                continue
            statement_words=set(re.findall(r'[a-z0-9]+',(fact.statement+' '+fact.value+' '+(fact.unit or '')).lower()))
            stop_words = {"and", "the", "for", "from", "with", "that", "this", "into"}
            meaningful={
                word for word in statement_words
                if len(word) > 2
                and word not in stop_words
                and document_term_frequency.get(word, 0) == 1
            }
            matched_terms = words & meaningful
            overlap = max(
                len(matched_terms) / max(1, len(meaningful)),
                0.25 if matched_terms else 0.0,
            )
            retrieval_score = overlap
            if matched_terms:
                retrieval_score = max(
                    retrieval_score,
                    hybrid_similarity(
                        claim,
                        fact.statement+' '+fact.value+' '+(fact.unit or ''),
                    ) * 0.9,
                )
            if idx in claim_vectors and fact.id in fact_vectors:
                retrieval_score=max(retrieval_score,max(0.0,cosine(claim_vectors[idx],fact_vectors[fact.id])))
            if retrieval_score>=0.22: scored.append((retrieval_score,fact))
        scored.sort(
            key=lambda pair: rerank_scores.get(pair[1].id, pair[0]),
            reverse=True,
        )
        scored = scored[:3]
        if scored:
            score,fact=scored[0]
            start=fact.valid_from; end=fact.valid_to
            if start and start.tzinfo is None: start=start.replace(tzinfo=timezone.utc)
            if end and end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
            evidence.append({'type':'approved_fact','id':fact.id,'code':fact.code,'statement':fact.statement,'value':fact.value,'unit':fact.unit,'source_ref':fact.source_ref,'version':fact.version,'valid_from':fact.valid_from.isoformat() if fact.valid_from else None,'valid_to':fact.valid_to.isoformat() if fact.valid_to else None,'match_score':round(score,2)})
            if fact_outside_validity_window(start, end, now):
                verdict='outdated'; rationale=f"The closest matching approved fact ({fact.code}, v{fact.version}) is outside its validity window. Confirm the current value before publishing."; severity='critical'
            elif re.search(r'\d+(?:\.\d+)?\s*%?',claim) or re.search(r'₹|\brs\.?\s*\d|\binr\s*\d', claim, re.I):
                numeric_match=compare_claim_to_fact(claim, fact.value, fact.unit)
                if numeric_match is True:
                    verdict='supported'; rationale=f"A current approved fact matches the numeric value after common unit normalization (source: {fact.source_ref}, v{fact.version}). Context remains subject to human review."; severity='advisory'
                elif numeric_match is False:
                    verdict='contradicted'; rationale=f"The claim's normalized numeric value differs from the closest matching approved fact (source: {fact.source_ref}, v{fact.version})."; severity='major'
                else:
                    verdict='needs_human_review'; rationale=f"A related approved fact was found (source: {fact.source_ref}, v{fact.version}), but its units could not be safely compared."; severity='major'
            elif score>=0.35:
                nli_label = None
                if evaluation_variant in {"retrieval_and_nli", "full_pipeline"}:
                    masked_claim, claim_mask_count, _ = await mask_model_input(claim)
                    fact_source = f"{fact.statement} {fact.value} {fact.unit or ''}".strip()
                    masked_evidence, evidence_mask_count, _ = await mask_model_input(fact_source)
                    if masking_failed:
                        verdict='needs_human_review'; severity='major'
                        rationale="Sensitive-data masking failed; no NLI call was made."
                    else:
                        nli_started = time.perf_counter()
                        nli = await ollama_nli(
                            masked_claim, masked_evidence,
                            settings.ollama_base_url, settings.ollama_model,
                        )
                        db.add(AICall(
                            workspace_id=user.workspace_id,
                            revision_id=revision.id,
                            provider="ollama",
                            model=settings.ollama_model,
                            purpose="claim_fact_nli",
                            input_chars=len(masked_claim) + len(masked_evidence),
                            masked_entities=claim_mask_count + evidence_mask_count,
                            duration_ms=int((time.perf_counter() - nli_started) * 1000),
                            status=nli.get("status", "needs_human_review"),
                        ))
                        nli_label = nli.get("label")
                        if nli.get("status") != "completed" or nli_label == "unknown":
                            verdict='needs_human_review'; severity='major'
                            rationale="Local NLI failed or could not determine the relationship; a reviewer must assess the claim."
                if verdict is None and provider is not None and not masking_failed:
                    masked_claim, claim_mask_count, _ = await mask_model_input(claim)
                    fact_source = f"{fact.statement} {fact.value} {fact.unit or ''}".strip()
                    masked_evidence, evidence_mask_count, fact_mask_map = await mask_model_input(fact_source)
                    try:
                        if masking_failed:
                            raise ModelStepFailed("Sensitive-data masking failed.")
                        rule_version = hashlib.sha256(
                            "|".join(
                                f"{rule.code}:{rule.version}"
                                for rule in sorted(rules, key=lambda rule: rule.code)
                            ).encode()
                        ).hexdigest()
                        adjudication_key = hashlib.sha256(
                            f"{user.workspace_id}:adjudication:{provider.name}:{provider.model}:"
                            f"{rule_version}:{masked_claim}:{masked_evidence}".encode()
                        ).hexdigest()
                        cached_adjudication = await db.scalar(select(CheckCache).where(
                            CheckCache.key == adjudication_key,
                            CheckCache.workspace_id == user.workspace_id,
                        ))
                        if cached_adjudication:
                            adjudication = Adjudication.model_validate(cached_adjudication.result_json)
                        else:
                            call_rows = {}
                            started_at = {}

                            async def log_adjudication_call(status, attempt):
                                if status == "started":
                                    started_at[attempt] = time.perf_counter()
                                    row = AICall(
                                        workspace_id=user.workspace_id,
                                        revision_id=revision.id,
                                        provider=provider.name,
                                        model=provider.model,
                                        purpose="claim_fact_adjudication",
                                        input_chars=len(masked_claim) + len(masked_evidence),
                                        masked_entities=claim_mask_count + evidence_mask_count,
                                        status="started",
                                    )
                                    db.add(row)
                                    call_rows[attempt] = row
                                    await db.flush()
                                elif attempt in call_rows:
                                    call_rows[attempt].status = status
                                    call_rows[attempt].duration_ms = int(
                                        (time.perf_counter() - started_at[attempt]) * 1000
                                    )

                            adjudication = await validated_json(
                                provider,
                                system_prompt=(
                                    "Adjudicate only against the supplied approved fact. "
                                    "Quote an exact substring of that fact."
                                ),
                                user_prompt=json.dumps({
                                    "claim": masked_claim,
                                    "fact_id": fact.id,
                                    "fact": masked_evidence,
                                }),
                                output_model=Adjudication,
                                on_call=log_adjudication_call,
                            )
                            db.add(CheckCache(
                                key=adjudication_key,
                                workspace_id=user.workspace_id,
                                result_json=adjudication.model_dump(),
                            ))
                        if not verify_adjudication_quote(
                            adjudication,
                            expected_fact_id=fact.id,
                            fact_text=fact_source,
                            masked_value_map=fact_mask_map,
                        ):
                            verdict='needs_human_review'; severity='major'
                            rationale="Model adjudication was discarded because its quote was not an exact substring of the stored fact."
                            evidence.append({"type":"invalid_model_quote","fact_id":fact.id})
                        elif nli_label and adjudication.verdict != nli_label:
                            verdict='needs_human_review'; severity='major'
                            rationale="The local NLI result and quote-validated adjudication disagreed; human review is required."
                        else:
                            verdict=adjudication.verdict
                            severity='advisory' if verdict == 'supported' else 'major'
                            rationale=f"{adjudication.reason} (verified quote from {fact.source_ref}, v{fact.version})."
                    except ModelStepFailed:
                        verdict='needs_human_review'; severity='major'
                        rationale="Model adjudication failed validation or was unavailable; a reviewer must assess the claim."
                elif verdict is None:
                    verdict='needs_human_review'; severity='major'
                    rationale=f"A related approved fact was found (source: {fact.source_ref}, v{fact.version}), but there is no exact deterministic comparison."
            else:
                if risky_claim:
                    rationale=f"A possible related fact was found (source: {fact.source_ref}, v{fact.version}), but the match is weak. Treat as unsupported pending review."; verdict='unsupported'; severity='major'
        # Rule evidence is only emitted when relevant to the claim or explicitly policy-matched.
        for rule in active_rules:
            applicable = not rule.channels or item.channel in (rule.channels or [])
            if not applicable: continue
            rw=set(re.findall(r'[a-z0-9]+',rule.text.lower())); meaningful_rw={w for w in rw if len(w)>3}
            overlap=len(words & meaningful_rw)/max(1,len(meaningful_rw))
            explicit_banned = rule.type.lower() in {'banned_term','terminology'} and any(term.strip().lower() in claim.lower() for term in re.split(r'[,;\n]',rule.text) if len(term.strip())>2)
            if overlap>=0.2 or explicit_banned:
                evidence.append({'type':'active_rule','id':rule.id,'code':rule.code,'title':rule.title,'text':rule.text,'version':rule.version,'severity':rule.severity,'source_ref':rule.source_ref})
                if verdict is None:
                    verdict='needs_human_review'
                    rationale=f"An active workspace rule ({rule.code}) applies; a reviewer must confirm this content."
                    severity='major'
                # Severity is governed by the matching rule, not inferred from a generic claim label.
                try:
                    candidate_severity=normalize_severity(rule.severity or 'major')
                except ValueError:
                    candidate_severity='major'
                severity_rank={'advisory':1,'major':2,'critical':3}
                if severity_rank.get(candidate_severity,2)>severity_rank.get(severity,1): severity=candidate_severity
                if explicit_banned and severity != 'critical':
                    severity='critical'
        term_assets=(await db.scalars(select(BrandAsset).where(BrandAsset.workspace_id==user.workspace_id,BrandAsset.kind=='term_list'))).all()
        for asset in term_assets:
            data=asset.data or {}
            banned=data.get('banned_terms',data.get('banned',[]))
            if isinstance(banned,str): banned=re.split(r'[,;\n]',banned)
            for term in banned if isinstance(banned,list) else []:
                if isinstance(term,str) and term.strip() and term.strip().lower() in claim.lower():
                    evidence.append({'type':'brand_term_list','id':asset.id,'code':'BRAND-BANNED-TERM','title':asset.name,'text':f'Banned term matched: {term.strip()}','source_ref':'Workspace brand term list'})
                    verdict='unsupported'; severity='critical'; rationale=f"The claim contains a term marked as banned in the workspace term list ({asset.name}). Human review is required."
        policy=_claim_builtin_policy(claim) if india_pack_enabled else None
        if policy:
            verdict, severity, code, rationale = policy
            evidence.append({'type':'policy_pack','code':code,'title':'India starter guidance','text':rationale,'source_ref':'BrandCourt starter policy pack (advisory; not legal advice)'})
        # Approved precedents are attached automatically only when the same rule/channel
        # applies and semantic similarity meets the shared 0.85 threshold. They never
        # alter the verdict or silence a critical finding.
        applicable_rule_ids = {
            evidence_item.get("rule_id") or evidence_item.get("id")
            for evidence_item in evidence
            if evidence_item.get("type") == "active_rule"
            and (evidence_item.get("rule_id") or evidence_item.get("id"))
        }
        for applicable_rule_id in applicable_rule_ids:
            for score, precedent in matching_approved_precedents(
                precedents, rule_id=applicable_rule_id, channel=item.channel,
                pattern_text=claim,
            ):
                evidence.append({
                    'type': 'approved_precedent', 'id': precedent.id,
                    'rule_id': precedent.rule_id, 'channel': precedent.channel,
                    'pattern_text': precedent.pattern_text, 'reason': precedent.reason,
                    'valid_to': precedent.valid_to.isoformat() if precedent.valid_to else None,
                    'match_score': round(score, 4),
                    'notice': 'Advisory only; reviewer confirmation is required and verdict/severity are unchanged.',
                })
        if verdict is None or (
            not risky_claim
            and not any(e.get('type') in {'active_rule', 'brand_term_list', 'policy_pack'} for e in evidence)
        ):
            continue
        claim_span=claim_records[idx] if idx < len(claim_records) else {}
        finding=ClaimFinding(
            workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,
            claim_text=claim,verdict=verdict,rationale=rationale,evidence=evidence,
            severity=severity,layer='claims',span_start=claim_span.get('span_start'),
            span_end=claim_span.get('span_end'),
            suggested_fix=("Attach a current approved fact or revise the claim." if verdict in {'unsupported','needs_human_review'} else None),
            analysis_method='deterministic_v2',
        )
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
        if job and idx % 5 == 0:
            await progress(min(85, 55 + int(30*(idx+1)/max(1,min(len(claims),100)))), 'claims')
    await progress(90, 'tone')
    tone_examples=(await db.scalars(
        select(RuleExample.text).join(Rule, Rule.id==RuleExample.rule_id).where(
            Rule.workspace_id==user.workspace_id, Rule.status=='active',
            Rule.type=='brand_voice', RuleExample.kind.in_(['approved','positive','on_brand']),
        )
    )).all()
    brand_voice = workspace_settings.get("brand_voice", [])
    if isinstance(brand_voice, dict):
        brand_voice = (
            brand_voice.get("examples")
            or brand_voice.get("approved_examples")
            or brand_voice.get("positive")
            or []
        )
    if isinstance(brand_voice, str):
        brand_voice = [brand_voice]
    if not isinstance(brand_voice, list):
        brand_voice = []
    voice_examples = []
    for value in [*tone_examples, *brand_voice]:
        if isinstance(value, str) and value.strip():
            voice_examples.append(value.strip())
        elif isinstance(value, dict) and isinstance(value.get("text"), str):
            if value.get("kind", "approved") in {"approved", "positive", "on_brand"}:
                voice_examples.append(value["text"].strip())
    for tone in advisory_tone(text, voice_examples) if run_visual_checks else []:
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text=text[:1000] or '[creative metadata]',verdict='needs_human_review',rationale=tone['message'],evidence=[{'type':'tone_advisory','code':tone['code'],'text':tone['message'],'confidence':tone.get('confidence')}],severity='advisory',layer='tone',intent_check={'confidence':tone.get('confidence')},analysis_method='tone_heuristic')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    stored_findings=(await db.scalars(select(ClaimFinding).where(
        ClaimFinding.workspace_id==user.workspace_id,
        ClaimFinding.revision_id==revision.id,
    ))).all()
    finding_by_id={finding.id:finding for finding in stored_findings}
    merged=merge_overlapping_spans([{
        "id":finding.id,"claim_text":finding.claim_text,"verdict":finding.verdict,
        "rationale":finding.rationale,"evidence":finding.evidence or [],
        "severity":finding.severity,"layer":finding.layer,
        "span_start":finding.span_start,"span_end":finding.span_end,
        "suggested_fix":finding.suggested_fix,
    } for finding in stored_findings])
    for merged_finding in merged:
        record=finding_by_id.get(merged_finding.get("id"))
        if not record:
            continue
        record.span_start=merged_finding.get("span_start")
        record.span_end=merged_finding.get("span_end")
        record.severity=merged_finding.get("severity")
        record.verdict=merged_finding.get("verdict")
        record.rationale=merged_finding.get("rationale")
        record.evidence=merged_finding.get("evidence") or []
        record.layer=merged_finding.get("layer") or record.layer
        record.suggested_fix=merged_finding.get("suggested_fix")
        if record.span_start is not None and record.span_end is not None:
            record.claim_text=text[record.span_start:record.span_end] or record.claim_text
        for duplicate_id in merged_finding.get("finding_ids", [])[1:]:
            duplicate=finding_by_id.get(duplicate_id)
            if duplicate:
                await db.delete(duplicate)
    await db.flush()
    outputs=[finding_view(finding) for finding in (
        await db.scalars(select(ClaimFinding).where(
            ClaimFinding.workspace_id==user.workspace_id,
            ClaimFinding.revision_id==revision.id,
        ))
    ).all()]
    await progress(100, 'complete')
    item.status='analyzed'
    await write_audit(db,user,'claim_court.analysis_completed',{'content_id':item.id,'revision_id':revision.id,'claims':len(outputs),'method':'deterministic_v2'})
    result={'content_id':item.id,'revision_id':revision.id,'revision_version':revision.version,'analysis_method':'deterministic_v2','evaluation_variant':evaluation_variant,'language':language_info,'privacy':{'masked_entities_for_model_input':masked_count,'external_model_called':bool(provider and provider.name != 'ollama'),'local_model_called':model_mode=='ollama' and not masking_failed},'notice':('Model-assisted checking plus deterministic policy checks were used; model calls are logged and inputs are masked. ' if provider and provider.name != 'disabled' else 'Deterministic checks with exact comparisons and advisory India starter policy checks. ')+'This is not legal advice; human review is required.','findings':outputs,'summary':{v:sum(1 for x in outputs if x['verdict']==v) for v in ['supported','contradicted','outdated','unsupported','needs_human_review']}}
    return jsonable_encoder(result)


async def _run_analysis_job(job_id: str, content_id: str, workspace_id: str, user_id: str):
    from app.core.job_worker import process_job

    await process_job(job_id, worker_id=f"compat-{uuid4().hex[:12]}")


@router.post('/content/{content_id}/analyze', status_code=202)
async def analyze_content(
    content_id: str,
    user: CurrentUser,
    db: DBSession,
    evaluation_variant: str | None = Query(
        default=None,
        pattern="^(code_rules_only|retrieval_and_nli|full_pipeline)$",
    ),
):
    role_check(user, ANALYZE_ROLES)
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    revision=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not revision: raise HTTPException(409,'No current content revision exists.')
    if item.status == 'approved' or revision.locked_at is not None:
        raise HTTPException(409,'Approved revision is locked. Reopen the item before running a new analysis.')
    if evaluation_variant and user.role != "admin":
        raise HTTPException(403, "Only workspace admins may select an evaluation variant.")
    if evaluation_variant:
        await enforce_analyze_rate_limit(
            db,
            user,
            scope=f"evaluation:{evaluation_variant}",
            max_requests=EVALUATION_REQUEST_LIMIT,
        )
    else:
        await enforce_analyze_rate_limit(db, user)
    job=await enqueue_review_job(db,user,item,revision)
    if evaluation_variant:
        job.result = {"_evaluation_variant": evaluation_variant}
    await write_audit(db,user,'claim_court.analysis_queued',{'content_id':item.id,'revision_id':revision.id,'job_id':job.id,'evaluation_variant':evaluation_variant})
    await db.commit(); await db.refresh(job)
    return {'job_id':job.id,'status':job.status,'progress':job.progress,'stage':job.stage,'content_id':item.id,'revision_id':revision.id,'poll_url':f'/api/jobs/{job.id}'}


@router.get('/jobs/{job_id}')
async def get_review_job(job_id: str, user: CurrentUser, db: DBSession):
    job=await db.scalar(select(ReviewJob).where(ReviewJob.id==job_id,ReviewJob.workspace_id==user.workspace_id))
    if not job: raise HTTPException(404,'Review job not found.')
    return {'job_id':job.id,'content_id':job.content_id,'revision_id':job.revision_id,'status':job.status,'progress':job.progress,'stage':job.stage,'result':job.result if job.status == "completed" else None,'error':job.error,'created_at':job.created_at.isoformat(),'started_at':job.started_at.isoformat() if job.started_at else None,'finished_at':job.finished_at.isoformat() if job.finished_at else None}

@router.get('/content/{content_id}/findings')
async def get_findings(content_id: str, user: CurrentUser, db: DBSession):
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    revision=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not revision: return []
    rows=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.revision_id==revision.id,ClaimFinding.workspace_id==user.workspace_id).order_by(ClaimFinding.created_at))).all()
    return [finding_view(x) for x in rows]
