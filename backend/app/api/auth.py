from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from app.api.deps import DBSession, CurrentUser, require_roles, write_audit
from app.models.entities import User, Workspace
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(tags=['authentication'])
class RegisterWorkspace(BaseModel):
    workspace_name: str = Field(min_length=2, max_length=160)
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class LoginRequest(BaseModel): email: EmailStr; password: str
class CreateUser(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern='^(creator|reviewer|manager|admin)$')

def user_view(user: User):
    return {'id': user.id, 'workspace_id': user.workspace_id, 'email': user.email, 'full_name': user.full_name, 'role': user.role, 'is_active': user.is_active, 'created_at': user.created_at}
def token_view(user: User):
    return {'access_token': create_access_token(user.id, user.workspace_id, user.role), 'token_type':'bearer', 'user': user_view(user)}

@router.post('/auth/register-workspace', status_code=201)
async def register_workspace(body: RegisterWorkspace, db: DBSession):
    email = body.email.lower().strip()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, 'An account with this email already exists.')
    workspace = Workspace(name=body.workspace_name.strip())
    db.add(workspace); await db.flush()
    user = User(workspace_id=workspace.id, email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role='admin')
    db.add(user); await db.flush()
    await write_audit(db, user, 'workspace.created', {'workspace_name': workspace.name})
    await db.commit(); await db.refresh(user)
    return token_view(user)

@router.post('/auth/login')
async def login(body: LoginRequest, db: DBSession):
    email = body.email.lower().strip()
    users = (await db.scalars(select(User).where(User.email == email, User.is_active.is_(True)))).all()
    user = next((candidate for candidate in users if verify_password(body.password, candidate.password_hash)), None)
    if not user: raise HTTPException(401, 'Email or password is incorrect.')
    return token_view(user)

@router.get('/me')
async def me(user: CurrentUser): return user_view(user)

@router.get('/users')
async def list_users(user: CurrentUser, db: DBSession):
    users = (await db.scalars(select(User).where(User.workspace_id == user.workspace_id).order_by(User.created_at.desc()))).all()
    return [user_view(item) for item in users]

@router.post('/users', status_code=201)
async def create_user(body: CreateUser, user: CurrentUser, db: DBSession):
    if user.role != 'admin': raise HTTPException(403, 'Only a guideline owner (admin) can manage workspace members.')
    email = body.email.lower().strip()
    if await db.scalar(select(User.id).where(User.workspace_id == user.workspace_id, User.email == email)):
        raise HTTPException(409, 'This email already belongs to a member of this workspace.')
    member = User(workspace_id=user.workspace_id, email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role=body.role)
    db.add(member); await db.flush(); await write_audit(db, user, 'workspace.member_created', {'member_id': member.id, 'role': member.role})
    await db.commit(); await db.refresh(member)
    return user_view(member)

@router.patch('/users/{user_id}/role')
async def update_user_role(user_id: str, role: str, user: CurrentUser, db: DBSession):
    if user.role != 'admin': raise HTTPException(403, 'Only a guideline owner can change roles.')
    if role not in {'creator','reviewer','manager','admin'}: raise HTTPException(422, 'Unsupported role.')
    member = await db.scalar(select(User).where(User.id == user_id, User.workspace_id == user.workspace_id))
    if not member: raise HTTPException(404, 'Member not found in this workspace.')
    if member.id == user.id and role != 'admin': raise HTTPException(400, 'You cannot remove your own guideline-owner access.')
    old_role = member.role; member.role = role
    await write_audit(db, user, 'workspace.member_role_changed', {'member_id': member.id, 'from': old_role, 'to': role})
    await db.commit(); await db.refresh(member)
    return user_view(member)
