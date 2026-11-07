import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import AuditEvent, User, Workspace


def test_audit_events_cannot_be_updated_or_deleted_through_orm():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        workspace = Workspace(name="Workspace")
        session.add(workspace)
        session.flush()
        user = User(
            workspace_id=workspace.id,
            email="admin@example.test",
            full_name="Admin",
            password_hash="test-hash",
            role="admin",
        )
        session.add(user)
        session.flush()
        event = AuditEvent(workspace_id=workspace.id, actor_id=user.id, type="test.event", payload={})
        session.add(event)
        session.commit()

        event.type = "test.changed"
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()

        session.delete(event)
        with pytest.raises(ValueError, match="append-only"):
            session.commit()


def test_audit_event_json_payload_mutations_are_guarded():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        workspace = Workspace(name="Workspace")
        session.add(workspace)
        session.flush()
        event = AuditEvent(workspace_id=workspace.id, type="test.event", payload={"state": "original"})
        session.add(event)
        session.commit()

        event.payload["state"] = "changed"
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
