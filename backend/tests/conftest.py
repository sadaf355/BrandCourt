import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.entities import ContentItem, ContentRevision, Fact, User, Workspace


@pytest.fixture
def test_database(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        poolclass=NullPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    yield sessions
    asyncio.run(engine.dispose())


@pytest.fixture
def workspace_users(test_database):
    async def seed():
        async with test_database() as session:
            users = {}
            workspaces = [
                Workspace(name="Workspace One", settings={}),
                Workspace(name="Workspace Two", settings={}),
            ]
            session.add_all(workspaces)
            await session.flush()
            password_hash = hash_password("test-password-123")
            for workspace_number, workspace in enumerate(workspaces, start=1):
                for role in ("creator", "reviewer", "manager", "admin"):
                    user = User(
                        workspace_id=workspace.id,
                        email=f"{role}-{workspace_number}@example.com",
                        full_name=f"{role.title()} {workspace_number}",
                        password_hash=password_hash,
                        role=role,
                        is_active=True,
                    )
                    session.add(user)
                    await session.flush()
                    users[(workspace_number, role)] = user.id
                creator_id = users[(workspace_number, "creator")]
                session.add(
                    Fact(
                        workspace_id=workspace.id,
                        code=f"FACT-{workspace_number}",
                        statement=f"Workspace {workspace_number} fact",
                        value=str(workspace_number),
                        source_ref="test source",
                        version=1,
                        status="active",
                        created_by=creator_id,
                    )
                )
            content = ContentItem(
                workspace_id=workspaces[0].id,
                title="Test creative",
                channel="website",
                campaign="",
                status="draft",
                current_revision=1,
                created_by=users[(1, "creator")],
            )
            session.add(content)
            await session.flush()
            session.add(
                ContentRevision(
                    workspace_id=workspaces[0].id,
                    content_id=content.id,
                    version=1,
                    caption="",
                    created_by=users[(1, "creator")],
                )
            )
            await session.commit()
            return users, content.id, {number: workspace.id for number, workspace in enumerate(workspaces, start=1)}

    return asyncio.run(seed())


@pytest.fixture
def api_client(test_database):
    async def override_get_db():
        async with test_database() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    def request(method: str, path: str, **kwargs):
        async def send():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    yield request
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_headers(workspace_users):
    users, _content_id, workspace_ids = workspace_users

    def headers(workspace_number: int, role: str):
        user_id = users[(workspace_number, role)]
        token = create_access_token(user_id, workspace_ids[workspace_number], role)
        return {"Authorization": f"Bearer {token}"}

    return headers
