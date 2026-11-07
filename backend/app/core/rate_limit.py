import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import LoginRateLimit, User


async def enforce_analyze_rate_limit(
    db: AsyncSession,
    user: User,
    *,
    scope: str = "analyze",
    max_requests: int | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=settings.analyze_window_minutes)
    raw_key = f"{scope}\0{user.workspace_id}\0{user.id}".encode()
    key = hmac.new(settings.secret_key.encode(), raw_key, hashlib.sha256).hexdigest()
    request_limit = max_requests or settings.analyze_max_requests
    values = {"key": key, "failures": 1, "window_started_at": now}
    if db.bind.dialect.name == "postgresql":
        insert = postgres_insert(LoginRateLimit).values(**values)
    elif db.bind.dialect.name == "sqlite":
        insert = sqlite_insert(LoginRateLimit).values(**values)
    else:
        raise RuntimeError(f"Analyze rate limiting is unsupported for {db.bind.dialect.name}.")

    expired = LoginRateLimit.window_started_at <= cutoff
    await db.execute(
        insert.on_conflict_do_update(
            index_elements=[LoginRateLimit.key],
            set_={
                "failures": case(
                    (expired, 1),
                    else_=LoginRateLimit.failures + 1,
                ),
                "window_started_at": case((expired, now), else_=LoginRateLimit.window_started_at),
            },
        )
    )
    failures = await db.scalar(
        select(LoginRateLimit.failures).where(LoginRateLimit.key == key)
    )
    await db.commit()
    if failures and failures > request_limit:
        raise HTTPException(
            429,
            "Too many analysis requests. Try again after the rate-limit window.",
            headers={"Retry-After": str(settings.analyze_window_minutes * 60)},
        )
