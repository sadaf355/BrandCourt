from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from app.api.deps import DBSession, CurrentUser, write_audit
from app.models.entities import Fact, Precedent, ContentItem, User

router = APIRouter(prefix='/notifications', tags=['in-app notifications'])

class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    message: str
    link: str | None = None
    created_at: str
    read: bool = False

@router.get('', response_model=list[NotificationItem])
async def list_notifications(user: CurrentUser, db: DBSession):
    """
    Computes real-time workspace notifications based on domain state:
    1. Assigned / Submitted content waiting for review
    2. Facts expiring within 30 days or already expired
    3. Precedents awaiting manager approval
    """
    notifications: list[NotificationItem] = []
    now = datetime.now(timezone.utc)

    # 1. Content in review or submitted
    if user.role in {'reviewer', 'manager', 'admin'}:
        items = (await db.scalars(
            select(ContentItem)
            .where(ContentItem.workspace_id == user.workspace_id, ContentItem.status.in_(['submitted', 'in_review']))
            .order_by(desc(ContentItem.updated_at))
            .limit(10)
        )).all()
        for it in items:
            notifications.append(NotificationItem(
                id=f'notif-review-{it.id}',
                type='review_assigned',
                title='Content Awaiting Review',
                message=f'"{it.title}" is in {it.status} state and ready for reviewer sign-off.',
                link=f'/app/reviews/{it.id}',
                created_at=it.updated_at.isoformat(),
                read=False,
            ))

    # 2. Fact expiry warnings (valid_to nearing or passed)
    facts = (await db.scalars(
        select(Fact)
        .where(Fact.workspace_id == user.workspace_id, Fact.status == 'active', Fact.valid_to.is_not(None))
    )).all()
    for f in facts:
        if f.valid_to:
            diff_days = (f.valid_to - now).days
            if diff_days < 0:
                notifications.append(NotificationItem(
                    id=f'notif-fact-exp-{f.id}',
                    type='fact_expired',
                    title='Approved Fact Expired',
                    message=f'Fact "{f.code}" ({f.statement[:50]}...) has expired.',
                    link='/app/brand/facts',
                    created_at=now.isoformat(),
                    read=False,
                ))
            elif diff_days <= 30:
                notifications.append(NotificationItem(
                    id=f'notif-fact-warn-{f.id}',
                    type='fact_expiring_soon',
                    title='Fact Expiring Soon',
                    message=f'Fact "{f.code}" expires in {diff_days} day(s).',
                    link='/app/brand/facts',
                    created_at=now.isoformat(),
                    read=False,
                ))

    # 3. Precedents awaiting manager approval
    if user.role in {'manager', 'admin'}:
        precedents = (await db.scalars(
            select(Precedent)
            .where(Precedent.workspace_id == user.workspace_id, Precedent.status == 'pending')
            .order_by(desc(Precedent.created_at))
            .limit(10)
        )).all()
        for p in precedents:
            notifications.append(NotificationItem(
                id=f'notif-prec-{p.id}',
                type='precedent_approval',
                title='Precedent Pending Approval',
                message=f'A precedent for "{p.pattern_text[:40]}" requires manager approval before reuse.',
                link='/app/approvals',
                created_at=p.created_at.isoformat(),
                read=False,
            ))

    return notifications

