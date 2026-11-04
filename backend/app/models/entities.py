from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def uid() -> str: return str(uuid4())
def now_utc(): return datetime.now(timezone.utc)

class Workspace(Base):
    __tablename__ = 'workspaces'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('workspace_id', 'email', name='uq_user_workspace_email'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(254), index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default='creator', nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class GuidelineDoc(Base):
    __tablename__ = 'guideline_docs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, default='', nullable=False)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class Rule(Base):
    __tablename__ = 'rules'
    __table_args__ = (UniqueConstraint('workspace_id', 'code', 'version', name='uq_rule_workspace_code_version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey('guideline_docs.id', ondelete='SET NULL'), nullable=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(40), default='brand_voice', nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default='warning', nullable=False)
    channels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='draft', nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

class RuleExample(Base):
    __tablename__ = 'rule_examples'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_id: Mapped[str] = mapped_column(ForeignKey('rules.id', ondelete='CASCADE'), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class Fact(Base):
    __tablename__ = 'facts'
    __table_args__ = (UniqueConstraint('workspace_id', 'code', 'version', name='uq_fact_workspace_code_version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='active', nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class BrandAsset(Base):
    __tablename__ = 'assets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class ContentItem(Base):
    __tablename__ = 'content_items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    campaign: Mapped[str] = mapped_column(String(200), default='', nullable=False)
    status: Mapped[str] = mapped_column(String(30), default='draft', nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

class ContentRevision(Base):
    __tablename__ = 'content_revisions'
    __table_args__ = (UniqueConstraint('content_id', 'version', name='uq_content_revision_version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    content_id: Mapped[str] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(Text, default='', nullable=False)
    alt_text: Mapped[str] = mapped_column(Text, default='', nullable=False)
    is_ai_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detected_language: Mapped[str] = mapped_column(String(30), default='unknown', nullable=False)
    image_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    creative_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creative_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_text: Mapped[str] = mapped_column(Text, default='', nullable=False)
    ocr_status: Mapped[str] = mapped_column(String(30), default='not_run', nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    approved_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

class ClaimFinding(Base):
    __tablename__ = 'claim_findings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    content_id: Mapped[str] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'), index=True, nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey('content_revisions.id', ondelete='CASCADE'), index=True, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default='advisory', nullable=False)
    analysis_method: Mapped[str] = mapped_column(String(40), default='deterministic_v1', nullable=False)
    state: Mapped[str] = mapped_column(String(30), default='open', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ReviewComment(Base):
    __tablename__ = 'review_comments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    content_id: Mapped[str] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'), index=True, nullable=False)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey('claim_findings.id', ondelete='CASCADE'), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class FindingDecision(Base):
    __tablename__ = 'finding_decisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    finding_id: Mapped[str] = mapped_column(ForeignKey('claim_findings.id', ondelete='CASCADE'), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class Precedent(Base):
    __tablename__ = 'precedents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    finding_id: Mapped[str] = mapped_column(ForeignKey('claim_findings.id', ondelete='CASCADE'), index=True, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey('rules.id', ondelete='SET NULL'), nullable=True)
    channel: Mapped[str] = mapped_column(String(40), default='all', nullable=False)
    pattern_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewJob(Base):
    __tablename__ = 'review_jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    content_id: Mapped[str] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'), index=True, nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey('content_revisions.id', ondelete='CASCADE'), index=True, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='queued', nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str] = mapped_column(String(120), default='Queued', nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AICall(Base):
    __tablename__ = 'ai_calls'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    revision_id: Mapped[str | None] = mapped_column(ForeignKey('content_revisions.id', ondelete='SET NULL'), nullable=True)
    provider: Mapped[str] = mapped_column(String(80), default='deterministic', nullable=False)
    model: Mapped[str] = mapped_column(String(120), default='deterministic_baseline', nullable=False)
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    input_chars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    masked_entities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='completed', nullable=False)

class CheckCache(Base):
    __tablename__ = 'check_cache'
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey('content_revisions.id', ondelete='CASCADE'), index=True, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    json_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class Embedding(Base):
    __tablename__ = 'embeddings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    vector_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
