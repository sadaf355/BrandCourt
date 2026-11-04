"""Create the precedent ledger explicitly."""
from alembic import op
from app.db.base import Base
import app.models.entities

revision = '0005_intelligence_finish'
down_revision = '0004_image_workflow'
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.tables['precedents'].create(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    Base.metadata.tables['precedents'].drop(bind=op.get_bind(), checkfirst=True)
