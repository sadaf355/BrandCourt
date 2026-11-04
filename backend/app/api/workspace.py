from fastapi import APIRouter
from app.api.deps import CurrentUser, DBSession
from app.models.entities import Workspace
from sqlalchemy import select
router = APIRouter(tags=['workspace'])
@router.get('/workspace')
async def get_workspace(user: CurrentUser, db: DBSession):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    return {'id': user.workspace_id, 'name': workspace.name if workspace else 'Brand workspace', 'role': user.role}
