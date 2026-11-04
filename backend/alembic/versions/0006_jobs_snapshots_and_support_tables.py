"""Add review jobs, immutable approval snapshots and supporting tables.

This migration is intentionally explicit and can upgrade both a clean database and
an installation created by earlier BrandCourt builds.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.db.base import Base
import app.models.entities

revision = '0006_jobs_snapshots_support'
down_revision = '0005_intelligence_finish'
branch_labels = None
depends_on = None

TABLES = (
    'rule_examples', 'review_jobs', 'ai_calls', 'check_cache', 'reports', 'embeddings'
)

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'content_revisions' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('content_revisions')}
        with op.batch_alter_table('content_revisions') as batch:
            if 'locked_at' not in columns:
                batch.add_column(sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
            if 'approved_by' not in columns:
                batch.add_column(sa.Column('approved_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True))
            if 'approved_snapshot' not in columns:
                batch.add_column(sa.Column('approved_snapshot', sa.JSON(), nullable=True))
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)

def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
    inspector = inspect(bind)
    if 'content_revisions' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('content_revisions')}
        with op.batch_alter_table('content_revisions') as batch:
            if 'approved_snapshot' in columns:
                batch.drop_column('approved_snapshot')
            if 'approved_by' in columns:
                batch.drop_column('approved_by')
            if 'locked_at' in columns:
                batch.drop_column('locked_at')
