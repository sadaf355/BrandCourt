from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.db.base import Base
from app.models.entities import Rule, User, Workspace


def test_embeddings_use_json_on_sqlite_and_pgvector_on_postgresql():
    sqlite_engine = create_engine("sqlite://")
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as session:
        workspace = Workspace(name="Vector workspace", settings={})
        session.add(workspace)
        session.flush()
        user = User(
            workspace_id=workspace.id,
            email="vector@example.com",
            full_name="Vector User",
            password_hash="test-hash",
            role="admin",
        )
        session.add(user)
        session.flush()
        rule = Rule(
            workspace_id=workspace.id,
            code="VECTOR",
            title="Vector",
            text="A vectorized rule",
            type="claim",
            severity="major",
            channels=[],
            status="active",
            version=1,
            created_by=user.id,
            embedding=[0.25, -0.5, 1.0],
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)
        assert rule.embedding == [0.25, -0.5, 1.0]

    postgres_ddl = str(CreateTable(Rule.__table__).compile(dialect=postgresql.dialect()))
    assert "VECTOR" in postgres_ddl
