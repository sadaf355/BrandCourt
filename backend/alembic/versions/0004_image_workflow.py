"""Phase 6 image OCR metadata and Phase 7 review workflow."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
revision = '0004_image_workflow'
down_revision = '0003_content_claim_court'
branch_labels = None
depends_on = None
def upgrade():
    bind=op.get_bind(); inspector=inspect(bind)
    columns={c['name'] for c in inspector.get_columns('content_revisions')}
    with op.batch_alter_table('content_revisions') as batch:
        if 'ocr_text' not in columns: batch.add_column(sa.Column('ocr_text',sa.Text(),nullable=False,server_default=''))
        if 'ocr_status' not in columns: batch.add_column(sa.Column('ocr_status',sa.String(length=30),nullable=False,server_default='not_run'))
    inspector=inspect(bind); tables=set(inspector.get_table_names())
    if 'review_comments' not in tables:
        op.create_table('review_comments',sa.Column('id',sa.String(36),primary_key=True),sa.Column('workspace_id',sa.String(36),sa.ForeignKey('workspaces.id',ondelete='CASCADE'),nullable=False),sa.Column('content_id',sa.String(36),sa.ForeignKey('content_items.id',ondelete='CASCADE'),nullable=False),sa.Column('finding_id',sa.String(36),sa.ForeignKey('claim_findings.id',ondelete='CASCADE'),nullable=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('body',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    inspector=inspect(bind); indexes={x['name'] for x in inspector.get_indexes('review_comments')}
    if 'ix_review_comments_workspace_id' not in indexes: op.create_index('ix_review_comments_workspace_id','review_comments',['workspace_id'])
    if 'ix_review_comments_content_id' not in indexes: op.create_index('ix_review_comments_content_id','review_comments',['content_id'])
    inspector=inspect(bind); tables=set(inspector.get_table_names())
    if 'finding_decisions' not in tables:
        op.create_table('finding_decisions',sa.Column('id',sa.String(36),primary_key=True),sa.Column('workspace_id',sa.String(36),sa.ForeignKey('workspaces.id',ondelete='CASCADE'),nullable=False),sa.Column('finding_id',sa.String(36),sa.ForeignKey('claim_findings.id',ondelete='CASCADE'),nullable=False),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('action',sa.String(30),nullable=False),sa.Column('reason',sa.Text(),nullable=False,server_default=''),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    inspector=inspect(bind); indexes={x['name'] for x in inspector.get_indexes('finding_decisions')}
    if 'ix_finding_decisions_workspace_id' not in indexes: op.create_index('ix_finding_decisions_workspace_id','finding_decisions',['workspace_id'])
    if 'ix_finding_decisions_finding_id' not in indexes: op.create_index('ix_finding_decisions_finding_id','finding_decisions',['finding_id'])
def downgrade():
    bind=op.get_bind(); inspector=inspect(bind); tables=set(inspector.get_table_names())
    if 'finding_decisions' in tables:
        indexes={x['name'] for x in inspector.get_indexes('finding_decisions')}
        if 'ix_finding_decisions_finding_id' in indexes: op.drop_index('ix_finding_decisions_finding_id',table_name='finding_decisions')
        if 'ix_finding_decisions_workspace_id' in indexes: op.drop_index('ix_finding_decisions_workspace_id',table_name='finding_decisions')
        op.drop_table('finding_decisions')
    if 'review_comments' in tables:
        indexes={x['name'] for x in inspector.get_indexes('review_comments')}
        if 'ix_review_comments_content_id' in indexes: op.drop_index('ix_review_comments_content_id',table_name='review_comments')
        if 'ix_review_comments_workspace_id' in indexes: op.drop_index('ix_review_comments_workspace_id',table_name='review_comments')
        op.drop_table('review_comments')
    columns={c['name'] for c in inspect(bind).get_columns('content_revisions')}
    with op.batch_alter_table('content_revisions') as batch:
        if 'ocr_status' in columns: batch.drop_column('ocr_status')
        if 'ocr_text' in columns: batch.drop_column('ocr_text')
