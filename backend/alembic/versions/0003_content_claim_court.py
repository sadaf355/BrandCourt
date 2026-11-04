"""Create content, revision and Claim Court finding tables explicitly."""
from alembic import op
from app.db.base import Base
import app.models.entities

revision = '0003_content_claim_court'
down_revision = '0002_phase2_3'
branch_labels = None
depends_on = None

TABLES = ('content_items', 'content_revisions', 'claim_findings')

def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)

def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
