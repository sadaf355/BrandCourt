from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import asyncio
import re
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.core.guideline_files import extract_guideline_text
from app.core.storage import get_storage
from app.models.entities import GuidelineDoc, Rule, Fact, BrandAsset, AuditEvent
from app.services.image_upload import reencode_image

router = APIRouter(tags=['brand knowledge'])
ADMIN_ROLES = {'admin'}
EDITOR_ROLES = {'admin','manager'}

def ensure_role(user, roles):
    if user.role not in roles: raise HTTPException(403, 'You do not have permission to perform this action.')
def rule_view(x): return {'id':x.id,'workspace_id':x.workspace_id,'document_id':x.document_id,'code':x.code,'title':x.title,'text':x.text,'type':x.type,'severity':x.severity,'channels':x.channels or [],'status':x.status,'version':x.version,'source_ref':x.source_ref,'created_by':x.created_by,'confirmed_by':x.confirmed_by,'created_at':x.created_at,'updated_at':x.updated_at}
def fact_view(x):
    now = datetime.now(timezone.utc)
    end = x.valid_to
    start = x.valid_from
    if end and end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
    if start and start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    # Date-picker dates are inclusive calendar dates, not instants at midnight.
    expired = bool(end and (end.date() < now.date() if end.time().hour == 0 and end.time().minute == 0 and end.time().second == 0 else end < now))
    upcoming = bool(start and (start.date() > now.date() if start.time().hour == 0 and start.time().minute == 0 and start.time().second == 0 else start > now))
    status = 'expired' if expired else 'scheduled' if upcoming else x.status
    return {'id':x.id,'workspace_id':x.workspace_id,'code':x.code,'statement':x.statement,'value':x.value,'unit':x.unit,'valid_from':x.valid_from,'valid_to':x.valid_to,'source_ref':x.source_ref,'version':x.version,'status':status,'created_by':x.created_by,'created_at':x.created_at}
def asset_view(x): return {'id':x.id,'workspace_id':x.workspace_id,'kind':x.kind,'name':x.name,'data':x.data or {},'created_by':x.created_by,'updated_at':x.updated_at}
def slug_code(value):
    code = re.sub(r'[^A-Z0-9]+','-',value.upper()).strip('-')[:60]
    return code or f'RULE-{uuid4().hex[:8].upper()}'

class RuleCreate(BaseModel):
    code: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=3, max_length=10000)
    type: str = Field(default='brand_voice', pattern='^(brand_voice|claim|visual|disclosure|terminology|legal|term|pattern|required_text|approved_spelling|alt_text|other)$')
    severity: str = Field(default='major', pattern='^(critical|major|advisory)$')
    channels: list[str] = []
    source_ref: str | None = None
    document_id: str | None = None

class RulePatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    text: str | None = Field(default=None, min_length=3, max_length=10000)
    type: str | None = Field(default=None, pattern='^(brand_voice|claim|visual|disclosure|terminology|legal|term|pattern|required_text|approved_spelling|alt_text|other)$')
    severity: str | None = Field(default=None, pattern='^(critical|major|advisory)$')
    channels: list[str] | None = None
    source_ref: str | None = None
class FactCreate(BaseModel):
    code: str | None = Field(default=None, max_length=80)
    statement: str = Field(min_length=3, max_length=10000)
    value: str = Field(min_length=1, max_length=500)
    unit: str | None = Field(default=None, max_length=100)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source_ref: str = Field(min_length=2, max_length=500)
class AssetCreate(BaseModel):
    kind: str = Field(pattern='^(logo|palette|font|term_list|disclosure|other)$')
    name: str = Field(min_length=2, max_length=160)
    data: dict = {}
class AssetPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    data: dict | None = None

@router.get('/guidelines')
async def list_guidelines(user: CurrentUser, db: DBSession):
    docs = (await db.scalars(select(GuidelineDoc).where(GuidelineDoc.workspace_id == user.workspace_id).order_by(GuidelineDoc.created_at.desc()))).all()
    return [{'id':d.id,'filename':d.filename,'content_type':d.content_type,'uploaded_by':d.uploaded_by,'created_at':d.created_at,'extracted_characters':len(d.extracted_text),'proposed_rules':len((await db.scalars(select(Rule).where(Rule.document_id == d.id, Rule.workspace_id == user.workspace_id))).all())} for d in docs]

@router.post('/guidelines', status_code=201)
async def upload_guideline(user: CurrentUser, db: DBSession, file: UploadFile = File(...)):
    ensure_role(user, ADMIN_ROLES)
    filename = Path(file.filename or 'guideline.txt').name
    suffix = Path(filename).suffix.lower()
    if suffix not in {'.pdf','.docx','.txt'}: raise HTTPException(415, 'Supported guideline formats are PDF, DOCX and TXT.')
    raw = await file.read()
    if not raw: raise HTTPException(400, 'The uploaded file is empty.')
    if len(raw) > 20 * 1024 * 1024: raise HTTPException(413, 'Guidelines must be 20 MB or smaller.')
    try:
        text = extract_guideline_text(suffix, raw)
    except ValueError as exc:
        raise HTTPException(415, f'Guideline content is invalid for {suffix[1:].upper()}.') from exc
    storage_key = f'{user.workspace_id}/{uuid4().hex}{suffix}'
    try:
        await asyncio.to_thread(get_storage().put_bytes, storage_key, raw, file.content_type or 'application/octet-stream')
    except Exception as exc:
        raise HTTPException(503, 'Guideline storage is unavailable.') from exc
    doc = GuidelineDoc(workspace_id=user.workspace_id, filename=filename, content_type=file.content_type or 'application/octet-stream', storage_key=storage_key, extracted_text=text, uploaded_by=user.id)
    db.add(doc); await db.flush()
    # Extraction is intentionally a proposal generator: no extracted rule is active without human confirmation.
    candidates = []
    for line in text.splitlines():
        line = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*','',line).strip()
        if len(line) >= 18 and len(line) <= 600 and (line[-1] in '.!?' or re.match(r'^(must|never|always|do not|avoid|ensure|use|include|exclude|should|may not)\b', line, re.I)):
            candidates.append(line)
    # Keep document extraction useful without flooding the workspace with duplicate fragments.
    unique = list(dict.fromkeys(candidates))[:50]
    existing = (await db.scalars(select(Rule.code).where(Rule.workspace_id == user.workspace_id))).all()
    for index, line in enumerate(unique, 1):
        code = slug_code(f'{Path(filename).stem}-{index}')
        while code in existing: code = slug_code(f'{code}-{uuid4().hex[:4]}')
        existing.append(code)
        db.add(Rule(workspace_id=user.workspace_id, document_id=doc.id, code=code, title=(line[:90] + ('…' if len(line)>90 else '')), text=line, type='brand_voice', severity='major', channels=[], status='draft', version=1, source_ref=filename, created_by=user.id))
    await write_audit(db, user, 'guideline.uploaded', {'document_id':doc.id,'filename':filename,'proposed_rules':len(unique),'extracted_characters':len(text)})
    await db.commit(); await db.refresh(doc)
    return {'id':doc.id,'filename':doc.filename,'extracted_characters':len(text),'proposed_rules':len(unique),'message':'Document processed. Every proposed rule remains a draft until a guideline owner confirms it.'}

@router.get('/guidelines/{document_id}/text')
async def get_guideline_text(document_id: str, user: CurrentUser, db: DBSession):
    doc = await db.scalar(select(GuidelineDoc).where(GuidelineDoc.id == document_id, GuidelineDoc.workspace_id == user.workspace_id))
    if not doc: raise HTTPException(404, 'Guideline document not found.')
    return {'id':doc.id,'filename':doc.filename,'text':doc.extracted_text}

@router.get('/rules')
async def list_rules(user: CurrentUser, db: DBSession, status: str | None = None):
    query = select(Rule).where(Rule.workspace_id == user.workspace_id)
    if status: query = query.where(Rule.status == status)
    rows = (await db.scalars(query.order_by(Rule.updated_at.desc()))).all()
    return [rule_view(x) for x in rows]

@router.post('/rules', status_code=201)
async def create_rule(body: RuleCreate, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    code = slug_code(body.code or body.title)
    if await db.scalar(select(Rule.id).where(Rule.workspace_id == user.workspace_id, Rule.code == code, Rule.version == 1)):
        raise HTTPException(409, 'That rule code already exists. Choose a unique code.')
    if body.document_id and not await db.scalar(select(GuidelineDoc.id).where(GuidelineDoc.id == body.document_id, GuidelineDoc.workspace_id == user.workspace_id)):
        raise HTTPException(404, 'Guideline document not found in this workspace.')
    item = Rule(workspace_id=user.workspace_id, document_id=body.document_id, code=code, title=body.title.strip(), text=body.text.strip(), type=body.type, severity=body.severity, channels=body.channels, status='draft', version=1, source_ref=body.source_ref, created_by=user.id)
    db.add(item); await db.flush(); await write_audit(db, user, 'rule.created', {'rule_id':item.id,'code':item.code,'version':item.version})
    await db.commit(); await db.refresh(item); return rule_view(item)

@router.patch('/rules/{rule_id}')
async def update_rule(rule_id: str, body: RulePatch, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    item = await db.scalar(select(Rule).where(Rule.id == rule_id, Rule.workspace_id == user.workspace_id))
    if not item: raise HTTPException(404, 'Rule not found.')
    changes = body.model_dump(exclude_unset=True)
    if not changes: return rule_view(item)
    # Edits create a new version row, preserving the prior rule for auditability.
    new_data = {'workspace_id':item.workspace_id,'document_id':item.document_id,'code':item.code,'title':item.title,'text':item.text,'type':item.type,'severity':item.severity,'channels':item.channels,'status':'draft','version':item.version+1,'source_ref':item.source_ref,'created_by':user.id}
    new_data.update({k:v for k,v in changes.items() if v is not None})
    item.status = 'retired'
    new_item = Rule(**new_data)
    db.add(new_item); await db.flush(); await write_audit(db, user, 'rule.version_created', {'previous_rule_id':item.id,'rule_id':new_item.id,'code':new_item.code,'version':new_item.version})
    await db.commit(); await db.refresh(new_item); return rule_view(new_item)

@router.post('/rules/{rule_id}/confirm')
async def confirm_rule(rule_id: str, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    item = await db.scalar(select(Rule).where(Rule.id == rule_id, Rule.workspace_id == user.workspace_id))
    if not item: raise HTTPException(404, 'Rule not found.')
    if item.status == 'retired': raise HTTPException(409, 'Retired rules cannot be activated. Create a new version first.')
    item.status='active'; item.confirmed_by=user.id
    # Confirming a new version replaces any older active version of the same rule code.
    superseded = (await db.scalars(select(Rule).where(Rule.workspace_id == user.workspace_id, Rule.code == item.code, Rule.id != item.id, Rule.status == 'active'))).all()
    for older in superseded: older.status = 'retired'
    await write_audit(db, user, 'rule.confirmed', {'rule_id':item.id,'code':item.code,'version':item.version,'retired_rule_ids':[o.id for o in superseded]})
    await db.commit(); await db.refresh(item); return rule_view(item)

@router.post('/rules/{rule_id}/retire')
async def retire_rule(rule_id: str, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    item = await db.scalar(select(Rule).where(Rule.id == rule_id, Rule.workspace_id == user.workspace_id))
    if not item: raise HTTPException(404, 'Rule not found.')
    item.status='retired'; await write_audit(db, user, 'rule.retired', {'rule_id':item.id,'code':item.code,'version':item.version})
    await db.commit(); await db.refresh(item); return rule_view(item)

@router.get('/facts')
async def list_facts(user: CurrentUser, db: DBSession):
    rows = (await db.scalars(select(Fact).where(Fact.workspace_id == user.workspace_id).order_by(Fact.created_at.desc()))).all()
    return [fact_view(x) for x in rows]

@router.post('/facts', status_code=201)
async def create_fact(body: FactCreate, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    if body.valid_from and body.valid_to and body.valid_to < body.valid_from: raise HTTPException(422, 'valid_to must be on or after valid_from.')
    code = slug_code(body.code or body.statement[:50])
    existing = (await db.scalars(select(Fact).where(Fact.workspace_id == user.workspace_id, Fact.code == code).order_by(Fact.version.desc()))).first()
    version = existing.version + 1 if existing else 1
    item = Fact(workspace_id=user.workspace_id, code=code, statement=body.statement.strip(), value=body.value.strip(), unit=body.unit, valid_from=body.valid_from, valid_to=body.valid_to, source_ref=body.source_ref.strip(), version=version, status='active', created_by=user.id)
    db.add(item); await db.flush(); await write_audit(db, user, 'fact.created', {'fact_id':item.id,'code':item.code,'version':item.version})
    await db.commit(); await db.refresh(item); return fact_view(item)

@router.patch('/facts/{fact_id}')
async def revise_fact(fact_id: str, body: FactCreate, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    old = await db.scalar(select(Fact).where(Fact.id == fact_id, Fact.workspace_id == user.workspace_id))
    if not old: raise HTTPException(404, 'Fact not found.')
    if body.valid_from and body.valid_to and body.valid_to < body.valid_from: raise HTTPException(422, 'valid_to must be on or after valid_from.')
    old.status='superseded'
    new = Fact(workspace_id=user.workspace_id, code=old.code, statement=body.statement.strip(), value=body.value.strip(), unit=body.unit, valid_from=body.valid_from, valid_to=body.valid_to, source_ref=body.source_ref.strip(), version=old.version+1, status='active', created_by=user.id)
    db.add(new); await db.flush(); await write_audit(db, user, 'fact.version_created', {'previous_fact_id':old.id,'fact_id':new.id,'code':new.code,'version':new.version})
    await db.commit(); await db.refresh(new); return fact_view(new)

@router.get('/assets')
async def list_assets(user: CurrentUser, db: DBSession):
    rows = (await db.scalars(select(BrandAsset).where(BrandAsset.workspace_id == user.workspace_id).order_by(BrandAsset.updated_at.desc()))).all()
    return [asset_view(x) for x in rows]

@router.post('/assets', status_code=201)
async def create_asset(body: AssetCreate, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    if body.kind == 'logo':
        raise HTTPException(422, 'Upload logo image bytes through POST /api/assets/logo.')
    item = BrandAsset(workspace_id=user.workspace_id, kind=body.kind, name=body.name.strip(), data=body.data, created_by=user.id)
    db.add(item); await db.flush(); await write_audit(db, user, 'asset.created', {'asset_id':item.id,'kind':item.kind,'name':item.name})
    await db.commit(); await db.refresh(item); return asset_view(item)

@router.post('/assets/logo', status_code=201)
async def upload_logo_asset(
    user: CurrentUser,
    db: DBSession,
    name: str = Form(min_length=2, max_length=160),
    file: UploadFile = File(...),
):
    ensure_role(user, ADMIN_ROLES)
    filename = Path(file.filename or 'logo').name
    suffix = Path(filename).suffix.lower()
    if suffix not in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
        raise HTTPException(415, 'Supported logo formats: PNG, JPG, WEBP and GIF.')
    raw = await file.read(10 * 1024 * 1024 + 1)
    if not raw:
        raise HTTPException(400, 'Logo image must not be empty.')
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, 'Logo image must be no larger than 10 MB.')
    try:
        processed, thumbnail, width, height = reencode_image(raw, suffix)
    except OverflowError as exc:
        raise HTTPException(413, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    upload_id = uuid4().hex
    original_key = f'{user.workspace_id}/brand-assets/{upload_id}.original{suffix}'
    storage_key = f'{user.workspace_id}/brand-assets/{upload_id}.webp'
    thumbnail_key = f'{user.workspace_id}/brand-assets/{upload_id}.thumbnail.webp'
    original_content_type = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.webp': 'image/webp', '.gif': 'image/gif',
    }[suffix]
    try:
        storage = get_storage()
        await asyncio.to_thread(storage.put_bytes, original_key, raw, original_content_type)
        await asyncio.to_thread(storage.put_bytes, storage_key, processed, 'image/webp')
        await asyncio.to_thread(storage.put_bytes, thumbnail_key, thumbnail, 'image/webp')
    except Exception as exc:
        raise HTTPException(503, 'Logo storage is unavailable.') from exc
    item = BrandAsset(
        workspace_id=user.workspace_id,
        kind='logo',
        name=name.strip(),
        data={
            'storage_key': storage_key,
            'original_storage_key': original_key,
            'thumbnail_storage_key': thumbnail_key,
            'width': width,
            'height': height,
            'aspect_ratio': width / height,
        },
        created_by=user.id,
    )
    db.add(item)
    await db.flush()
    await write_audit(db, user, 'asset.logo_uploaded', {'asset_id': item.id, 'name': item.name})
    await db.commit()
    await db.refresh(item)
    return asset_view(item)

@router.patch('/assets/{asset_id}')
async def update_asset(asset_id: str, body: AssetPatch, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    item = await db.scalar(select(BrandAsset).where(BrandAsset.id == asset_id, BrandAsset.workspace_id == user.workspace_id))
    if not item: raise HTTPException(404, 'Asset not found.')
    if item.kind == 'logo' and body.data is not None:
        raise HTTPException(422, 'Uploaded logo storage metadata cannot be edited; upload a replacement logo instead.')
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None: setattr(item, key, value)
    await write_audit(db, user, 'asset.updated', {'asset_id':item.id,'kind':item.kind})
    await db.commit(); await db.refresh(item); return asset_view(item)

@router.delete('/assets/{asset_id}', status_code=204)
async def delete_asset(asset_id: str, user: CurrentUser, db: DBSession):
    ensure_role(user, ADMIN_ROLES)
    item = await db.scalar(select(BrandAsset).where(BrandAsset.id == asset_id, BrandAsset.workspace_id == user.workspace_id))
    if not item: raise HTTPException(404, 'Asset not found.')
    await write_audit(db, user, 'asset.deleted', {'asset_id':item.id,'kind':item.kind})
    await db.delete(item); await db.commit(); return None

@router.get('/audit-events')
async def list_audit_events(user: CurrentUser, db: DBSession, limit: int = 50):
    if user.role not in {'admin','manager','reviewer'}: raise HTTPException(403, 'Audit events are available to reviewers, managers and guideline owners.')
    limit = max(1, min(limit, 200))
    rows = (await db.scalars(select(AuditEvent).where(AuditEvent.workspace_id == user.workspace_id).order_by(AuditEvent.created_at.desc()).limit(limit))).all()
    return [{'id':x.id,'actor_id':x.actor_id,'type':x.type,'payload':x.payload,'created_at':x.created_at} for x in rows]
