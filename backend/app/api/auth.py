import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.api.deps import DBSession, CurrentUser, write_audit
from app.core.config import settings
from app.models.entities import LoginRateLimit, RefreshToken, User, Workspace
from app.services.demo_workspace import is_demo_ready, set_demo_ready, get_demo_workspace_id
from app.core.security import (
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)

router = APIRouter(tags=['authentication'])
class RegisterWorkspace(BaseModel):
    workspace_name: str = Field(min_length=2, max_length=160)
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    workspace_id: str | None = None
class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)
class DemoLoginRequest(BaseModel):
    role: str = Field(default="admin")
class CreateUser(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern='^(creator|reviewer|manager|admin)$')

def user_view(user: User):
    return {'id': user.id, 'workspace_id': user.workspace_id, 'email': user.email, 'full_name': user.full_name, 'role': user.role, 'is_active': user.is_active, 'created_at': user.created_at}
def _new_refresh_token(user: User) -> tuple[str, RefreshToken]:
    token = secrets.token_urlsafe(48)
    
    record = RefreshToken(
        workspace_id=user.workspace_id,
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    )
    return token, record


def token_view(user: User, refresh_token: str):
    return {
        'access_token': create_access_token(user.id, user.workspace_id, user.role),
        'refresh_token': refresh_token,
        'token_type':'bearer',
        'user': user_view(user),
    }

@router.post('/auth/register-workspace', status_code=201)
async def register_workspace(body: RegisterWorkspace, db: DBSession):
    email = body.email.lower().strip()
    workspace = Workspace(name=body.workspace_name.strip())
    db.add(workspace); await db.flush()
    user = User(workspace_id=workspace.id, email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role='admin')
    db.add(user); await db.flush()
    await write_audit(db, user, 'workspace.created', {'workspace_name': workspace.name})
    refresh_token, refresh_record = _new_refresh_token(user)
    db.add(refresh_record)
    await db.commit(); await db.refresh(user)
    return token_view(user, refresh_token)

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    return request.client.host if request.client else "unknown"


@router.post('/auth/login')
async def login(body: LoginRequest, request: Request, db: DBSession):
    email = body.email.lower().strip()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=settings.login_window_minutes)
    client_ip = get_client_ip(request)
    key = hmac.new(
        settings.secret_key.encode(),
        f"{client_ip}\0{email}".encode(),
        hashlib.sha256,
    ).hexdigest()
    blocked = await db.scalar(
        select(LoginRateLimit.failures).where(
            LoginRateLimit.key == key,
            LoginRateLimit.window_started_at > cutoff,
            LoginRateLimit.failures >= settings.login_max_failures,
        )
    )
    if blocked:
        raise HTTPException(
            429,
            "Too many failed sign-in attempts. Try again after the rate-limit window.",
            headers={"Retry-After": str(settings.login_window_minutes * 60)},
        )

    user_query = select(User).where(User.email == email, User.is_active.is_(True))
    if body.workspace_id:
        user_query = user_query.where(User.workspace_id == body.workspace_id)
    users = (await db.scalars(user_query)).all()
    matching_users = [
        candidate
        for candidate in users
        if verify_password(body.password, candidate.password_hash)
    ]
    if not matching_users:
        values = {"key": key, "failures": 1, "window_started_at": now}
        if db.bind.dialect.name == "postgresql":
            insert = postgres_insert(LoginRateLimit).values(**values)
        else:
            insert = sqlite_insert(LoginRateLimit).values(**values)
        expired = LoginRateLimit.window_started_at <= cutoff
        await db.execute(
            insert.on_conflict_do_update(
                index_elements=[LoginRateLimit.key],
                set_={
                    "failures": case(
                        (expired, 1),
                        else_=LoginRateLimit.failures + 1,
                    ),
                    "window_started_at": case(
                        (expired, now),
                        else_=LoginRateLimit.window_started_at,
                    ),
                },
            )
        )
        await db.commit()
        raise HTTPException(401, 'Email or password is incorrect.')
    if len(matching_users) > 1:
        raise HTTPException(
            409,
            "This email belongs to multiple workspaces. Specify workspace_id to sign in.",
        )
    user = matching_users[0]

    rate_limit = await db.get(LoginRateLimit, key)
    if rate_limit:
        await db.delete(rate_limit)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    refresh_token, refresh_record = _new_refresh_token(user)
    db.add(refresh_record)
    await db.commit()
    return token_view(user, refresh_token)


@router.get('/auth/demo-status')
async def demo_status(db: DBSession):
    enabled = settings.demo_login_enabled
    ready = False
    if enabled:
        if is_demo_ready():
            ready = True
        else:
            ws_id = await get_demo_workspace_id(db)
            if ws_id:
                admin_user = await db.scalar(
                    select(User.id).where(
                        User.workspace_id == ws_id,
                        User.email == settings.demo_admin_email,
                        User.is_active.is_(True),
                    ).limit(1)
                )
                if admin_user:
                    set_demo_ready(True)
                    ready = True
    return {'enabled': enabled, 'ready': ready}


@router.post('/auth/demo-login')
async def demo_login(
    request: Request,
    db: DBSession,
    body: DemoLoginRequest | None = None,
):
    if not settings.demo_login_enabled:
        raise HTTPException(404, 'Demo login is disabled.')

    role = (body.role if body and body.role else 'admin').lower().strip()
    role_email_map = {
        'admin': settings.demo_admin_email,
        'creator': 'creator@glowserum.com',
        'reviewer': 'reviewer@glowserum.com',
        'manager': 'manager@glowserum.com',
    }
    if role not in role_email_map:
        raise HTTPException(422, 'Role must be one of: admin, creator, reviewer, manager.')

    # Rate limiting keyed by client IP
    client_ip = get_client_ip(request)
    key = hmac.new(
        settings.secret_key.encode(),
        f"{client_ip}\0demo-login".encode(),
        hashlib.sha256,
    ).hexdigest()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=settings.login_window_minutes)

    blocked = await db.scalar(
        select(LoginRateLimit.failures).where(
            LoginRateLimit.key == key,
            LoginRateLimit.window_started_at > cutoff,
            LoginRateLimit.failures >= settings.login_max_failures,
        )
    )
    if blocked:
        raise HTTPException(
            429,
            'Too many sign-in attempts. Try again after the rate-limit window.',
            headers={'Retry-After': str(settings.login_window_minutes * 60)},
        )

    # Upsert rate limit attempt
    values = {'key': key, 'failures': 1, 'window_started_at': now}
    if db.bind.dialect.name == 'postgresql':
        insert = postgres_insert(LoginRateLimit).values(**values)
    else:
        insert = sqlite_insert(LoginRateLimit).values(**values)
    expired = LoginRateLimit.window_started_at <= cutoff
    await db.execute(
        insert.on_conflict_do_update(
            index_elements=[LoginRateLimit.key],
            set_={
                'failures': case(
                    (expired, 1),
                    else_=LoginRateLimit.failures + 1,
                ),
                'window_started_at': case(
                    (expired, now),
                    else_=LoginRateLimit.window_started_at,
                ),
            },
        )
    )
    await db.commit()

    if not is_demo_ready():
        demo_ws_id = await get_demo_workspace_id(db)
        if demo_ws_id:
            admin_user = await db.scalar(
                select(User.id).where(
                    User.workspace_id == demo_ws_id,
                    User.email == settings.demo_admin_email,
                    User.is_active.is_(True),
                ).limit(1)
            )
            if admin_user:
                set_demo_ready(True)
        else:
            from app.services.demo_workspace import _provisioning_lock, run_demo_startup_provisioning
            import asyncio
            if not _provisioning_lock.locked():
                asyncio.create_task(run_demo_startup_provisioning())

    if not is_demo_ready():
        raise HTTPException(503, 'Demo is preparing, try again in a minute')

    demo_ws_id = await get_demo_workspace_id(db)
    if not demo_ws_id:
        raise HTTPException(503, 'Demo is preparing, try again in a minute')

    demo_ws = await db.get(Workspace, demo_ws_id)
    if not demo_ws or not dict(demo_ws.settings or {}).get('is_demo'):
        raise HTTPException(503, 'Demo is preparing, try again in a minute')

    target_email = role_email_map[role]
    user = await db.scalar(
        select(User).where(
            User.workspace_id == demo_ws_id,
            User.email == target_email,
            User.is_active.is_(True),
        )
    )
    if not user:
        raise HTTPException(503, 'Demo is preparing, try again in a minute')

    await write_audit(
        db,
        user,
        'auth.demo_login',
        {'role': role, 'email': user.email, 'workspace_id': user.workspace_id},
    )
    refresh_token, refresh_record = _new_refresh_token(user)
    db.add(refresh_record)
    await db.commit()
    return token_view(user, refresh_token)


@router.post('/auth/refresh')
async def refresh_access_token(body: RefreshRequest, db: DBSession):
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    current = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    if not current:
        raise HTTPException(401, 'Refresh token is invalid, expired, or revoked.')
    if current.revoked_at is not None:
        if current.replaced_by is not None:
            await _revoke_user_refresh_tokens(db, current, now, "reuse_detected")
        raise HTTPException(401, 'Refresh token is invalid, expired, or revoked.')
    expires_at = current.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        current.revoked_at = now
        await db.commit()
        raise HTTPException(401, 'Refresh token is invalid, expired, or revoked.')

    user = await db.scalar(
        select(User).where(
            User.id == current.user_id,
            User.workspace_id == current.workspace_id,
            User.is_active.is_(True),
        )
    )
    if not user:
        current.revoked_at = now
        await db.commit()
        raise HTTPException(401, 'Refresh token is invalid, expired, or revoked.')

    next_token, next_record = _new_refresh_token(user)
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == current.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        await db.rollback()
        raced_token = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if raced_token and raced_token.revoked_at and raced_token.replaced_by:
            await _revoke_user_refresh_tokens(db, raced_token, now, "reuse_detected")
        raise HTTPException(401, 'Refresh token is invalid, expired, or revoked.')
    db.add(next_record)
    await db.flush()
    current.replaced_by = next_record.id
    await write_audit(
        db,
        user,
        'auth.refresh_token_rotated',
        {'previous_token_id': current.id, 'refresh_token_id': next_record.id},
    )
    await db.commit()
    return token_view(user, next_token)


async def _revoke_user_refresh_tokens(
    db: DBSession,
    reused_token: RefreshToken,
    now: datetime,
    reason: str,
) -> None:
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == reused_token.user_id,
            RefreshToken.workspace_id == reused_token.workspace_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    user = await db.scalar(
        select(User).where(
            User.id == reused_token.user_id,
            User.workspace_id == reused_token.workspace_id,
        )
    )
    if user:
        await write_audit(
            db,
            user,
            'auth.refresh_token_reuse_detected',
            {'refresh_token_id': reused_token.id, 'reason': reason},
        )
    await db.commit()


@router.post('/auth/logout')
async def revoke_refresh_token(body: RefreshRequest, db: DBSession):
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    current = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 1 and current:
        user = await db.scalar(
            select(User).where(
                User.id == current.user_id,
                User.workspace_id == current.workspace_id,
            )
        )
        if user:
            await write_audit(
                db,
                user,
                'auth.refresh_token_revoked',
                {'refresh_token_id': current.id},
            )
    await db.commit()
    return {'revoked': result.rowcount == 1}

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
