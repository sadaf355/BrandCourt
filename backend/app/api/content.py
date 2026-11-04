from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import re
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.models.entities import ContentItem, ContentRevision, ClaimFinding, Fact, Rule, Precedent, ReviewJob, User, BrandAsset, Embedding, AICall
from app.db.session import SessionLocal
from app.services.claim_policy import _normalized_number_comparison, _claim_builtin_policy
from app.services.text_intelligence import mask_sensitive, detect_language, layer1_checks, advisory_tone
from app.services.semantic_retrieval import embedding, hybrid_similarity, ollama_nli, ollama_embeddings, cosine

router = APIRouter(tags=['content review and Claim Court'])
EDIT_ROLES = {'creator', 'admin', 'manager'}
ANALYZE_ROLES = {'creator', 'reviewer', 'manager', 'admin'}

def role_check(user, roles):
    if user.role not in roles:
        raise HTTPException(403, 'Your workspace role does not permit this action.')

def item_view(x):
    return {'id':x.id,'title':x.title,'channel':x.channel,'campaign':x.campaign,'status':x.status,'current_revision':x.current_revision,'created_by':x.created_by,'created_at':x.created_at,'updated_at':x.updated_at}
def revision_view(x):
    return {'id':x.id,'content_id':x.content_id,'version':x.version,'caption':x.caption,'creative_filename':x.creative_filename,'ocr_status':getattr(x,'ocr_status','not_run'),'ocr_text':getattr(x,'ocr_text',''),'alt_text':getattr(x,'alt_text',''),'is_ai_media':getattr(x,'is_ai_media',False),'detected_language':getattr(x,'detected_language','unknown'),'image_analysis':getattr(x,'image_analysis',None),'created_by':x.created_by,'created_at':x.created_at}
def finding_view(x):
    return {'id':x.id,'claim_text':x.claim_text,'verdict':x.verdict,'rationale':x.rationale,'evidence':x.evidence or [],'severity':x.severity,'analysis_method':x.analysis_method,'state':getattr(x,'state','open'),'created_at':x.created_at}

class ContentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    channel: str = Field(pattern='^(website|instagram|facebook|linkedin|email|paid_ad|packaging|other)$')
    campaign: str = Field(default='', max_length=200)
    caption: str = Field(default='', max_length=30000)
    alt_text: str = Field(default='', max_length=3000)
    is_ai_media: bool = False
class ContentEdit(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    channel: str | None = Field(default=None, pattern='^(website|instagram|facebook|linkedin|email|paid_ad|packaging|other)$')
    campaign: str | None = Field(default=None, max_length=200)
    caption: str | None = Field(default=None, max_length=30000)
    alt_text: str | None = Field(default=None, max_length=3000)
    is_ai_media: bool | None = None

@router.get('/content')
async def list_content(user: CurrentUser, db: DBSession):
    rows = (await db.scalars(select(ContentItem).where(ContentItem.workspace_id==user.workspace_id).order_by(desc(ContentItem.updated_at)))).all()
    return [item_view(x) for x in rows]

@router.post('/content', status_code=201)
async def create_content(body: ContentCreate, user: CurrentUser, db: DBSession):
    role_check(user, EDIT_ROLES)
    item = ContentItem(workspace_id=user.workspace_id,title=body.title.strip(),channel=body.channel,campaign=body.campaign.strip(),status='draft',current_revision=1,created_by=user.id)
    db.add(item); await db.flush()
    revision = ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=1,caption=body.caption,alt_text=body.alt_text,is_ai_media=body.is_ai_media,detected_language=detect_language(body.caption)['language'],created_by=user.id)
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
    revision = ContentRevision(workspace_id=user.workspace_id,content_id=item.id,version=version,caption=caption,alt_text=alt_text,is_ai_media=is_ai_media,detected_language=detect_language(caption)['language'],creative_filename=latest.creative_filename if latest else None,creative_storage_key=latest.creative_storage_key if latest else None,image_analysis=latest.image_analysis if latest else None,ocr_text=latest.ocr_text if latest else '',ocr_status=latest.ocr_status if latest else 'not_run',created_by=user.id)
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
    if suffix not in {'.png','.jpg','.jpeg','.webp','.gif','.svg'}: raise HTTPException(415,'Supported creative formats: PNG, JPG, WEBP, GIF and SVG.')
    raw=await file.read()
    if not raw: raise HTTPException(400,'Creative must not be empty.')
    if len(raw)>10*1024*1024: raise HTTPException(413,'Creative must be no larger than 10 MB.')
    if suffix=='.svg':
        # Validate SVG as XML and reject active/embedded content rather than trusting the filename.
        import xml.etree.ElementTree as ET
        lowered=raw.lower()
        if b'<!doctype' in lowered or b'<!entity' in lowered or b'javascript:' in lowered or b'data:text/html' in lowered:
            raise HTTPException(415,'SVG contains active or embedded content and was rejected.')
        try:
            root=ET.fromstring(raw)
        except ET.ParseError as exc:
            raise HTTPException(415,'SVG file is not valid XML.') from exc
        if root.tag.split('}')[-1].lower()!='svg':
            raise HTTPException(415,'Uploaded file content does not match the SVG extension.')
        for element in root.iter():
            tag=element.tag.split('}')[-1].lower()
            if tag in {'script','foreignobject','iframe','object','embed'}:
                raise HTTPException(415,'SVG contains active content and was rejected.')
            for attr,value in element.attrib.items():
                attr_name=attr.split('}')[-1].lower()
                if attr_name.startswith('on') or 'javascript:' in value.lower() or 'data:text/html' in value.lower():
                    raise HTTPException(415,'SVG contains active content and was rejected.')
    else:
        # Verify the actual image bytes and their decoded format, not only the extension.
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(raw)) as image:
                expected={'.png':'PNG','.jpg':'JPEG','.jpeg':'JPEG','.webp':'WEBP','.gif':'GIF'}[suffix]
                if image.format != expected:
                    raise HTTPException(415,'Uploaded file content does not match its image extension.')
                if image.width*image.height > 40_000_000:
                    raise HTTPException(413,'Image dimensions exceed the 40 megapixel safety limit.')
                image.verify()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(415,'Uploaded file is not a valid supported image.') from exc
    folder=Path(settings.upload_dir)/user.workspace_id/'creatives'; folder.mkdir(parents=True,exist_ok=True)
    key=f'{user.workspace_id}/creatives/{uuid4().hex}{suffix}'; (Path(settings.upload_dir)/key).write_bytes(raw)
    latest=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id).order_by(desc(ContentRevision.version)))
    if not latest: raise HTTPException(409,'Create a content revision before uploading a creative.')
    latest.creative_filename=filename; latest.creative_storage_key=key; latest.ocr_text=''; latest.ocr_status='not_run'; latest.image_analysis=None
    await write_audit(db,user,'content.creative_uploaded',{'content_id':item.id,'revision_id':latest.id,'filename':filename})
    await db.commit(); await db.refresh(latest)
    return revision_view(latest)

async def _perform_analysis(db, user, item, revision, job=None):
    async def progress(value, stage):
        if job:
            job.progress = value; job.stage = stage
            # Commit progress so another request can observe it while the job runs.
            await db.commit()
    await progress(10, 'Preparing current revision')
    old=(await db.scalars(select(ClaimFinding).where(ClaimFinding.revision_id==revision.id,ClaimFinding.workspace_id==user.workspace_id))).all()
    for finding in old: await db.delete(finding)
    text='\n'.join(part for part in [revision.caption.strip(), (revision.ocr_text or '').strip()] if part)
    language_info=detect_language(text)
    revision.detected_language=language_info['language']
    masked_text, masked_count=mask_sensitive(text)
    # No external provider is called in deterministic mode. Log the input that would be sent after masking.
    db.add(AICall(workspace_id=user.workspace_id,revision_id=revision.id,provider='deterministic',model='deterministic_baseline',purpose='claim_court_review',input_chars=len(masked_text),masked_entities=masked_count,status='completed'))
    claims=[re.sub(r'\s+',' ',part).strip(' •\t') for part in re.split(r'(?<=[.!?])\s+|\n+',text) if len(part.strip())>=12]
    facts=(await db.scalars(select(Fact).where(Fact.workspace_id==user.workspace_id,Fact.status=='active'))).all()
    rules=(await db.scalars(select(Rule).where(Rule.workspace_id==user.workspace_id,Rule.status=='active'))).all()
    now=datetime.now(timezone.utc); outputs=[]
    claim_vectors: dict[int, list[float]] = {}
    fact_vectors: dict[str, list[float]] = {}
    # Optional local semantic embeddings. Every input is masked before it leaves this process.
    # If the local embedding service is down, keep deterministic retrieval but make the failure visible.
    if settings.model_mode.lower() == 'ollama' and claims and facts:
        import time
        embedding_inputs=[]; embedding_mask_count=0
        for source in [*claims[:100], *[(f.statement+' '+str(f.value)+' '+(f.unit or '')).strip() for f in facts]]:
            masked_source, count=mask_sensitive(source)
            embedding_inputs.append(masked_source[:3000]); embedding_mask_count += count
        started=time.perf_counter()
        embedded=await ollama_embeddings(embedding_inputs,settings.ollama_base_url,settings.ollama_embedding_model)
        db.add(AICall(workspace_id=user.workspace_id,revision_id=revision.id,provider='ollama',model=settings.ollama_embedding_model,purpose='claim_retrieval_embeddings',input_chars=sum(map(len,embedding_inputs)),masked_entities=embedding_mask_count,duration_ms=int((time.perf_counter()-started)*1000),status=embedded.get('status','needs_human_review')))
        if embedded.get('status') == 'completed':
            vectors=embedded['embeddings']; claim_count=min(len(claims),100)
            claim_vectors={i:vectors[i] for i in range(claim_count)}
            for fact_index,fact in enumerate(facts):
                vector=vectors[claim_count+fact_index]
                fact_vectors[fact.id]=vector
                model_key=f'ollama:{settings.ollama_embedding_model}'
                existing_embedding=await db.scalar(select(Embedding.id).where(Embedding.workspace_id==user.workspace_id,Embedding.entity_type=='fact',Embedding.entity_id==fact.id,Embedding.model==model_key))
                if existing_embedding:
                    stored=await db.scalar(select(Embedding).where(Embedding.id==existing_embedding))
                    if stored: stored.vector_json=vector
                else:
                    db.add(Embedding(workspace_id=user.workspace_id,entity_type='fact',entity_id=fact.id,model=model_key,vector_json=vector))
        else:
            message='Local embedding service is unavailable; deterministic retrieval is continuing, but semantic matching needs human review.'
            finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text='[semantic retrieval status]',verdict='needs_human_review',rationale=message,evidence=[{'type':'model_service','code':'LOCAL-EMBEDDING-UNAVAILABLE','text':embedded.get('reason',message),'source_ref':'Local Ollama embedding service'}],severity='warning',analysis_method='model_service_fallback')
            db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    # Persist deterministic hashing vectors for fallback retrieval and reproducible auditability.
    for entity_type, entities in [('fact', facts), ('rule', rules)]:
        for entity in entities:
            exists=await db.scalar(select(Embedding.id).where(Embedding.workspace_id==user.workspace_id,Embedding.entity_type==entity_type,Embedding.entity_id==entity.id,Embedding.model=='hashing-trigram-v1'))
            if not exists:
                source=(getattr(entity,'statement','')+' '+getattr(entity,'value','')+' '+getattr(entity,'text','')+' '+getattr(entity,'title','')).strip()
                db.add(Embedding(workspace_id=user.workspace_id,entity_type=entity_type,entity_id=entity.id,model='hashing-trigram-v1',vector_json=embedding(source)))
    await progress(30, 'Matching approved facts and active rules')
    for check in layer1_checks(text, item.channel, revision.alt_text if revision.creative_storage_key else 'not applicable', revision.is_ai_media):
        evidence=[{'type':'policy_pack','code':check['code'],'title':check['type'],'text':check['message'],'source_ref':'BrandCourt India starter guidance / accessibility reminder'}]
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text=text[:1000] or '[creative metadata]',verdict=check['verdict'],rationale=check['message'],evidence=evidence,severity=check['severity'],analysis_method='layer1_deterministic')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    for tone in advisory_tone(text):
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text=text[:1000] or '[creative metadata]',verdict='needs_human_review',rationale=tone['message'],evidence=[{'type':'tone_advisory','code':tone['code'],'text':tone['message']}],severity='advisory',analysis_method='tone_heuristic')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    image_result=revision.image_analysis or {}
    if image_result and image_result.get('overall_status')=='needs_human_review':
        visual_evidence=[{'type':'visual_check','code':'VISUAL-REVIEW','title':'Image intelligence review','text':'One or more visual checks failed or could not be verified. Human review is required.','image_analysis':image_result}]
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text='[image creative visual checks]',verdict='needs_human_review',rationale='Image intelligence reported a failed or unavailable check. This creative cannot be auto-cleared; inspect colour distance, contrast, logo verification and OCR boxes.',evidence=visual_evidence,severity='warning',analysis_method='image_intelligence_v1')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
    precedents=(await db.scalars(select(Precedent).where(Precedent.workspace_id==user.workspace_id,Precedent.status=='approved',(Precedent.valid_to.is_(None) | (Precedent.valid_to >= now)),(Precedent.channel=='all') | (Precedent.channel==item.channel)))).all()
    for idx, claim in enumerate(claims[:100]):
        words=set(re.findall(r'[a-z0-9]+',claim.lower()))
        evidence=[]; verdict='unverifiable'; rationale='No sufficiently specific approved fact was matched. This is not a finding that the claim is false.'; severity='advisory'
        scored=[]
        for fact in facts:
            statement_words=set(re.findall(r'[a-z0-9]+',(fact.statement+' '+fact.value+' '+(fact.unit or '')).lower()))
            meaningful={w for w in statement_words if len(w)>3}
            overlap=len(words & meaningful)/max(1,len(meaningful))
            retrieval_score=max(overlap, hybrid_similarity(claim, fact.statement+' '+fact.value+' '+(fact.unit or ''))*0.9)
            if idx in claim_vectors and fact.id in fact_vectors:
                retrieval_score=max(retrieval_score,max(0.0,cosine(claim_vectors[idx],fact_vectors[fact.id])))
            if retrieval_score>=0.22: scored.append((retrieval_score,fact))
        if scored:
            scored.sort(key=lambda pair:pair[0],reverse=True); score,fact=scored[0]
            start=fact.valid_from; end=fact.valid_to
            if start and start.tzinfo is None: start=start.replace(tzinfo=timezone.utc)
            if end and end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
            evidence.append({'type':'approved_fact','id':fact.id,'code':fact.code,'statement':fact.statement,'value':fact.value,'unit':fact.unit,'source_ref':fact.source_ref,'version':fact.version,'valid_from':fact.valid_from.isoformat() if fact.valid_from else None,'valid_to':fact.valid_to.isoformat() if fact.valid_to else None,'match_score':round(score,2)})
            if (end and end < now) or (start and start > now):
                verdict='outdated'; rationale=f"The closest matching approved fact ({fact.code}, v{fact.version}) is outside its validity window. Confirm the current value before publishing."; severity='critical'
            elif re.search(r'\d+(?:\.\d+)?\s*%?',claim) and re.search(r'\d+(?:\.\d+)?',fact.value):
                numeric_match=_normalized_number_comparison(claim, fact.value, fact.unit)
                if numeric_match is True:
                    verdict='supported'; rationale=f"A current approved fact matches the numeric value after common unit normalization (source: {fact.source_ref}, v{fact.version}). Context remains subject to human review."; severity='advisory'
                elif numeric_match is False:
                    verdict='contradicted'; rationale=f"The claim's normalized numeric value differs from the closest matching approved fact (source: {fact.source_ref}, v{fact.version})."; severity='critical'
                else:
                    verdict='unverifiable'; rationale=f"A related approved fact was found (source: {fact.source_ref}, v{fact.version}), but its units could not be safely compared."; severity='warning'
            elif score>=0.35:
                if settings.model_mode.lower() == 'ollama':
                    import time
                    started=time.perf_counter()
                    masked_claim, claim_mask_count=mask_sensitive(claim)
                    masked_evidence, evidence_mask_count=mask_sensitive(fact.statement+' '+fact.value+' '+(fact.unit or ''))
                    nli=await ollama_nli(masked_claim,masked_evidence,settings.ollama_base_url,settings.ollama_model)
                    db.add(AICall(workspace_id=user.workspace_id,revision_id=revision.id,provider='ollama',model=settings.ollama_model,purpose='claim_evidence_nli',input_chars=len(masked_claim)+len(masked_evidence),masked_entities=claim_mask_count+evidence_mask_count,duration_ms=int((time.perf_counter()-started)*1000),status=nli.get('status','needs_human_review')))
                    if nli['label']=='supported': verdict='supported'; severity='advisory'; rationale=f"Local NLI model found the claim supported by the approved fact: {nli['reason']} (source: {fact.source_ref}, v{fact.version}). Human review remains required."
                    elif nli['label']=='contradicted': verdict='contradicted'; severity='critical'; rationale=f"Local NLI model found a possible contradiction: {nli['reason']} (source: {fact.source_ref}, v{fact.version}). Human review required."
                    else: verdict='needs_human_review'; severity='warning'; rationale=f"Local NLI could not safely classify this claim: {nli['reason']}"
                else:
                    verdict='supported'; rationale=f"A current approved fact has overlapping terminology (source: {fact.source_ref}, v{fact.version}). This is lexical retrieval, not semantic proof; human review is required."; severity='advisory'
            else:
                rationale=f"A possible related fact was found (source: {fact.source_ref}, v{fact.version}), but the match is weak. Treat as unverifiable pending review."; verdict='unverifiable'
        # Rule evidence is only emitted when relevant to the claim or explicitly policy-matched.
        for rule in rules:
            applicable = not rule.channels or item.channel in (rule.channels or [])
            if not applicable: continue
            rw=set(re.findall(r'[a-z0-9]+',rule.text.lower())); meaningful_rw={w for w in rw if len(w)>3}
            overlap=len(words & meaningful_rw)/max(1,len(meaningful_rw))
            explicit_banned = rule.type.lower() in {'banned_term','terminology'} and any(term.strip().lower() in claim.lower() for term in re.split(r'[,;\n]',rule.text) if len(term.strip())>2)
            if overlap>=0.2 or explicit_banned:
                evidence.append({'type':'active_rule','id':rule.id,'code':rule.code,'title':rule.title,'text':rule.text,'version':rule.version,'severity':rule.severity,'source_ref':rule.source_ref})
                # Severity is governed by the matching rule, not inferred from a generic claim label.
                rule_severity=(rule.severity or 'warning').lower()
                candidate_severity=rule_severity if rule_severity in {'critical','blocker','warning','advisory','info'} else 'warning'
                severity_rank={'info':0,'advisory':1,'warning':2,'critical':3,'blocker':4}
                if severity_rank.get(candidate_severity,2)>severity_rank.get(severity,1): severity=candidate_severity
                if explicit_banned and severity not in {'critical','blocker'}:
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
        policy=_claim_builtin_policy(claim)
        if policy:
            verdict, severity, code, rationale = policy
            evidence.append({'type':'policy_pack','code':code,'title':'India starter guidance','text':rationale,'source_ref':'BrandCourt starter policy pack (advisory; not legal advice)'})
        for precedent in precedents:
            pattern_words={w for w in re.findall(r'[a-z0-9]+',precedent.pattern_text.lower()) if len(w)>2}
            if pattern_words:
                overlap=len(words & pattern_words)/len(pattern_words)
                if overlap>=0.35:
                    evidence.append({'type':'approved_precedent','id':precedent.id,'rule_id':precedent.rule_id,'channel':precedent.channel,'pattern_text':precedent.pattern_text,'reason':precedent.reason,'valid_to':precedent.valid_to.isoformat() if precedent.valid_to else None,'match_score':round(overlap,2),'notice':'Advisory reviewer precedent; not proof and does not determine the verdict.'})
        finding=ClaimFinding(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,claim_text=claim,verdict=verdict,rationale=rationale,evidence=evidence,severity=severity,analysis_method='deterministic_v2')
        db.add(finding); await db.flush(); outputs.append(finding_view(finding))
        if job and idx % 5 == 0:
            await progress(min(85, 35 + int(50*(idx+1)/max(1,min(len(claims),100)))), 'Checking claims and policy rules')
    item.status='analyzed'
    await write_audit(db,user,'claim_court.analysis_completed',{'content_id':item.id,'revision_id':revision.id,'claims':len(outputs),'method':'deterministic_v2'})
    result={'content_id':item.id,'revision_id':revision.id,'revision_version':revision.version,'analysis_method':'deterministic_v2','language':language_info,'privacy':{'masked_entities_for_model_input':masked_count,'external_model_called':False,'local_model_called':settings.model_mode.lower()=='ollama'},'notice':('Local Ollama embeddings/NLI plus deterministic policy checks were used; model calls are logged and inputs are masked. ' if settings.model_mode.lower()=='ollama' else 'Deterministic baseline with common duration-unit normalization and advisory India starter policy checks. ')+'This is not legal advice; human review is required.','findings':outputs,'summary':{v:sum(1 for x in outputs if x['verdict']==v) for v in ['supported','contradicted','outdated','unverifiable','unsupported','needs_human_review']}}
    return result


async def _run_analysis_job(job_id: str, content_id: str, workspace_id: str, user_id: str):
    async with SessionLocal() as db:
        job=await db.scalar(select(ReviewJob).where(ReviewJob.id==job_id,ReviewJob.workspace_id==workspace_id))
        item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==workspace_id))
        user=await db.scalar(select(User).where(User.id==user_id,User.workspace_id==workspace_id))
        if not job or not item or not user: return
        try:
            job.status='running'; job.progress=5; job.stage='Starting analysis'; job.started_at=datetime.now(timezone.utc)
            revision=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==workspace_id,ContentRevision.version==item.current_revision))
            if not revision: raise RuntimeError('Current revision no longer exists.')
            result=await _perform_analysis(db,user,item,revision,job)
            job.result=result; job.status='completed'; job.progress=100; job.stage='Analysis complete'; job.finished_at=datetime.now(timezone.utc)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            job=await db.scalar(select(ReviewJob).where(ReviewJob.id==job_id,ReviewJob.workspace_id==workspace_id))
            if job:
                job.status='failed'; job.stage='Analysis failed'; job.error=f'{type(exc).__name__}: {str(exc)[:400]}'; job.finished_at=datetime.now(timezone.utc)
                await db.commit()


@router.post('/content/{content_id}/analyze', status_code=202)
async def analyze_content(content_id: str, background_tasks: BackgroundTasks, user: CurrentUser, db: DBSession):
    role_check(user, ANALYZE_ROLES)
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    revision=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not revision: raise HTTPException(409,'No current content revision exists.')
    if item.status == 'approved' or revision.locked_at is not None:
        raise HTTPException(409,'Approved revision is locked. Reopen the item before running a new analysis.')
    job=ReviewJob(workspace_id=user.workspace_id,content_id=item.id,revision_id=revision.id,created_by=user.id,status='queued',progress=0,stage='Queued')
    db.add(job); await db.flush()
    await write_audit(db,user,'claim_court.analysis_queued',{'content_id':item.id,'revision_id':revision.id,'job_id':job.id})
    await db.commit(); await db.refresh(job)
    background_tasks.add_task(_run_analysis_job,job.id,item.id,user.workspace_id,user.id)
    return {'job_id':job.id,'status':job.status,'progress':job.progress,'stage':job.stage,'content_id':item.id,'revision_id':revision.id,'poll_url':f'/api/jobs/{job.id}'}


@router.get('/jobs/{job_id}')
async def get_review_job(job_id: str, user: CurrentUser, db: DBSession):
    job=await db.scalar(select(ReviewJob).where(ReviewJob.id==job_id,ReviewJob.workspace_id==user.workspace_id))
    if not job: raise HTTPException(404,'Review job not found.')
    return {'job_id':job.id,'content_id':job.content_id,'revision_id':job.revision_id,'status':job.status,'progress':job.progress,'stage':job.stage,'result':job.result,'error':job.error,'created_at':job.created_at.isoformat(),'started_at':job.started_at.isoformat() if job.started_at else None,'finished_at':job.finished_at.isoformat() if job.finished_at else None}

@router.get('/content/{content_id}/findings')
async def get_findings(content_id: str, user: CurrentUser, db: DBSession):
    item=await db.scalar(select(ContentItem).where(ContentItem.id==content_id,ContentItem.workspace_id==user.workspace_id))
    if not item: raise HTTPException(404,'Content item not found.')
    revision=await db.scalar(select(ContentRevision).where(ContentRevision.content_id==item.id,ContentRevision.workspace_id==user.workspace_id,ContentRevision.version==item.current_revision))
    if not revision: return []
    rows=(await db.scalars(select(ClaimFinding).where(ClaimFinding.content_id==item.id,ClaimFinding.revision_id==revision.id,ClaimFinding.workspace_id==user.workspace_id).order_by(ClaimFinding.created_at))).all()
    return [finding_view(x) for x in rows]
