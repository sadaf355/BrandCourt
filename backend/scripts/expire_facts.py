"""Daily idempotent fact expiry and notification job.

Schedule with the host's daily scheduler:
    python -m scripts.expire_facts
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Fact, Notification, User, Workspace


async def process_fact_expiry(
    sessions: Any = SessionLocal,
    *,
    now: datetime | None = None,
    notify_within_days: int = 30,
) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    notify_before = current + timedelta(days=notify_within_days)
    expired_count = 0
    notification_count = 0
    async with sessions() as db:
        workspace_ids = (await db.scalars(select(Workspace.id))).all()
        active_facts = []
        for workspace_id in workspace_ids:
            active_facts.extend((await db.scalars(
                select(Fact).where(
                    Fact.workspace_id == workspace_id,
                    Fact.status == "active",
                    Fact.valid_to.is_not(None),
                    Fact.valid_to <= notify_before,
                )
            )).all())
        users_by_workspace: dict[str, list[User]] = {}
        fact_workspace_ids = {fact.workspace_id for fact in active_facts}
        notified_facts: set[tuple[str, str, str]] = set()
        for workspace_id in fact_workspace_ids:
            existing_notifications = (await db.scalars(
                select(Notification).where(
                    Notification.workspace_id == workspace_id,
                    Notification.type.in_(("fact_expiring_soon", "fact_expired")),
                )
            )).all()
            notified_facts.update(
                (
                    row.workspace_id,
                    str((row.payload or {}).get("fact_id")),
                    row.type,
                )
                for row in existing_notifications
            )
        for fact in active_facts:
            valid_to = fact.valid_to
            if valid_to and valid_to.tzinfo is None:
                valid_to = valid_to.replace(tzinfo=timezone.utc)
            if valid_to and valid_to <= current:
                fact.status = "expired"
                expired_count += 1
                notification_type = "fact_expired"
                title = f"Approved fact expired: {fact.code}"
                body = f"{fact.statement} expired on {valid_to.date().isoformat()}."
            elif valid_to:
                notification_type = "fact_expiring_soon"
                title = f"Approved fact expiring soon: {fact.code}"
                body = f"{fact.statement} expires on {valid_to.date().isoformat()}."
            else:
                continue
            notification_key = (fact.workspace_id, fact.id, notification_type)
            if notification_key in notified_facts:
                continue
            recipients = users_by_workspace.get(fact.workspace_id)
            if recipients is None:
                recipients = (await db.scalars(
                    select(User).where(
                        User.workspace_id == fact.workspace_id,
                        User.is_active.is_(True),
                        User.role.in_(("manager", "admin")),
                    )
                )).all()
                users_by_workspace[fact.workspace_id] = recipients
            for recipient in recipients:
                db.add(
                    Notification(
                        workspace_id=fact.workspace_id,
                        user_id=recipient.id,
                        type=notification_type,
                        title=title,
                        body=body,
                        payload={
                            "fact_id": fact.id,
                            "fact_code": fact.code,
                            "valid_to": valid_to.isoformat(),
                        },
                    )
                )
                notification_count += 1
            notified_facts.add(notification_key)
        await db.commit()
    return {
        "facts_expired": expired_count,
        "notifications_created": notification_count,
    }


async def main(
    notify_within_days: int,
    watch: bool,
    interval_hours: float = 24,
) -> None:
    while True:
        result = await process_fact_expiry(notify_within_days=notify_within_days)
        print(json.dumps(result, sort_keys=True), flush=True)
        if not watch:
            return
        await asyncio.sleep(interval_hours * 60 * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify-within-days", type=int, default=30)
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run once at startup and then at the configured interval.",
    )
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=float(os.getenv("FACT_EXPIRY_INTERVAL_HOURS", "24")),
    )
    arguments = parser.parse_args()
    if arguments.notify_within_days < 1:
        parser.error("--notify-within-days must be positive")
    if arguments.interval_hours <= 0:
        parser.error("--interval-hours must be positive")
    asyncio.run(main(
        arguments.notify_within_days,
        arguments.watch,
        arguments.interval_hours,
    ))
