from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.entities import User
bearer = HTTPBearer(auto_error=False)
async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    if credentials is None: raise HTTPException(401, 'Authentication required.')
    claims = decode_access_token(credentials.credentials)
    user = await db.scalar(select(User).where(User.id == claims['sub'], User.workspace_id == claims['workspace_id'], User.is_active.is_(True)))
    if not user: raise HTTPException(401, 'User is inactive or no longer exists.')
    return user
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
def require_roles(*roles: str):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles: raise HTTPException(403, f"This action requires one of these roles: {', '.join(roles)}")
        return user
    return checker
async def write_audit(db: AsyncSession, user: User, event_type: str, payload: dict):
    from app.models.entities import AuditEvent
    db.add(AuditEvent(workspace_id=user.workspace_id, actor_id=user.id, type=event_type, payload=payload))
