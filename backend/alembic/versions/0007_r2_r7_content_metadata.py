"""R2-R7 content metadata and report/image workflow fields."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
revision = '0007_r2_r7_content_metadata'
down_revision = '0006_jobs_snapshots_support'
branch_labels = None
depends_on = None

def upgrade():
    columns={c['name'] for c in inspect(op.get_bind()).get_columns('content_revisions')}
    with op.batch_alter_table('content_revisions') as batch:
        if 'alt_text' not in columns: batch.add_column(sa.Column('alt_text', sa.Text(), nullable=False, server_default=''))
        if 'is_ai_media' not in columns: batch.add_column(sa.Column('is_ai_media', sa.Boolean(), nullable=False, server_default=sa.false()))
        if 'detected_language' not in columns: batch.add_column(sa.Column('detected_language', sa.String(length=30), nullable=False, server_default='unknown'))
        if 'image_analysis' not in columns: batch.add_column(sa.Column('image_analysis', sa.JSON(), nullable=True))
    finding_columns={c['name'] for c in inspect(op.get_bind()).get_columns('claim_findings')}
    if 'state' not in finding_columns:
        with op.batch_alter_table('claim_findings') as batch:
            batch.add_column(sa.Column('state', sa.String(length=30), nullable=False, server_default='open'))

def downgrade():
    columns={c['name'] for c in inspect(op.get_bind()).get_columns('content_revisions')}
    finding_columns={c['name'] for c in inspect(op.get_bind()).get_columns('claim_findings')}
    if 'state' in finding_columns:
        with op.batch_alter_table('claim_findings') as batch: batch.drop_column('state')
    with op.batch_alter_table('content_revisions') as batch:
        if 'image_analysis' in columns: batch.drop_column('image_analysis')
        if 'detected_language' in columns: batch.drop_column('detected_language')
        if 'is_ai_media' in columns: batch.drop_column('is_ai_media')
        if 'alt_text' in columns: batch.drop_column('alt_text')
