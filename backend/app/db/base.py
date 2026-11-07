from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata for all BrandCourt tables."""


@event.listens_for(Session, "before_flush")
def prevent_audit_event_mutations(session: Session, _flush_context, _instances) -> None:
    from app.models.entities import AuditEvent

    if any(isinstance(instance, AuditEvent) for instance in session.deleted):
        raise ValueError("Audit events are append-only and cannot be deleted.")
    if any(isinstance(instance, AuditEvent) for instance in session.dirty):
        raise ValueError("Audit events are append-only and cannot be modified.")
