"""Create workspace and brand knowledge tables explicitly."""
from alembic import op
from app.db.base import Base
import app.models.entities

revision = '0002_phase2_3'
down_revision = '0001_phase1'
branch_labels = None
depends_on = None

TABLES = ('workspaces', 'users', 'guideline_docs', 'rules', 'facts', 'assets', 'audit_events')

def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)

def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
