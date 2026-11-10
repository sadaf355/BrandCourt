import asyncio
import logging
import socket
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.entities import ContentItem, ContentRevision, ReviewJob, User

logger = logging.getLogger(__name__)
JobProcessor = Callable[[AsyncSession, ReviewJob], Awaitable[dict]]


async def _claim_job(
    sessions: async_sessionmaker[AsyncSession],
    worker_id: str,
    job_id: str | None = None,
) -> str | None:
    now = datetime.now(timezone.utc)
    async with sessions() as db:
        expired = and_(
            ReviewJob.status == "running",
            or_(
                ReviewJob.lease_expires_at.is_(None),
                ReviewJob.lease_expires_at <= now,
            ),
        )
        await db.execute(
            update(ReviewJob)
            .where(expired, ReviewJob.attempts >= ReviewJob.max_attempts)
            .values(
                status="failed",
                stage="Analysis failed after lease expiry",
                error="Worker lease expired after maximum attempts.",
                finished_at=now,
                lease_owner=None,
                lease_expires_at=None,
            )
        )
        eligible = or_(ReviewJob.status == "queued", expired)
        statement = select(ReviewJob.id).where(
            eligible,
            ReviewJob.attempts < ReviewJob.max_attempts,
        )
        if job_id is not None:
            statement = statement.where(ReviewJob.id == job_id)
        statement = statement.order_by(ReviewJob.created_at).limit(1)
        if db.bind.dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True)
        candidate_id = await db.scalar(statement)
        if candidate_id is None:
            await db.commit()
            return None

        updated_id = await db.scalar(
            update(ReviewJob)
            .where(
                ReviewJob.id == candidate_id,
                or_(
                    ReviewJob.status == "queued",
                    and_(
                        ReviewJob.status == "running",
                        or_(
                            ReviewJob.lease_expires_at.is_(None),
                            ReviewJob.lease_expires_at <= now,
                        ),
                    ),
                ),
                ReviewJob.attempts < ReviewJob.max_attempts,
            )
            .values(
                status="running",
                attempts=ReviewJob.attempts + 1,
                lease_owner=worker_id,
                lease_expires_at=now + timedelta(seconds=settings.job_lease_seconds),
                heartbeat_at=now,
                started_at=case(
                    (ReviewJob.started_at.is_(None), now),
                    else_=ReviewJob.started_at,
                ),
                finished_at=None,
                error=None,
                stage="Starting analysis",
            )
            .returning(ReviewJob.id)
        )
        await db.commit()
        return updated_id


async def _heartbeat(
    sessions: async_sessionmaker[AsyncSession],
    job_id: str,
    worker_id: str,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.job_heartbeat_seconds)
            return
        except TimeoutError:
            now = datetime.now(timezone.utc)
            async with sessions() as db:
                result = await db.execute(
                    update(ReviewJob)
                    .where(
                        ReviewJob.id == job_id,
                        ReviewJob.status == "running",
                        ReviewJob.lease_owner == worker_id,
                    )
                    .values(
                        heartbeat_at=now,
                        lease_expires_at=now + timedelta(seconds=settings.job_lease_seconds),
                    )
                )
                await db.commit()
                if result.rowcount != 1:
                    return


async def _perform_analysis_job(db: AsyncSession, job: ReviewJob) -> dict:
    from app.api.content import _perform_analysis

    user = await db.scalar(
        select(User).where(
            User.id == job.created_by,
            User.workspace_id == job.workspace_id,
            User.is_active.is_(True),
        )
    )
    item = await db.scalar(
        select(ContentItem).where(
            ContentItem.id == job.content_id,
            ContentItem.workspace_id == job.workspace_id,
        )
    )
    revision = await db.scalar(
        select(ContentRevision).where(
            ContentRevision.id == job.revision_id,
            ContentRevision.workspace_id == job.workspace_id,
            ContentRevision.content_id == job.content_id,
        )
    )
    if not user or not item or not revision:
        raise RuntimeError("The job's workspace content or active user no longer exists.")
    return await _perform_analysis(db, user, item, revision, job)


async def process_job(
    job_id: str,
    worker_id: str,
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
    processor: JobProcessor | None = None,
) -> bool:
    claimed_id = await _claim_job(sessions, worker_id, job_id)
    if claimed_id is None:
        return False
    return await _execute_claimed_job(claimed_id, worker_id, sessions, processor)


async def _execute_claimed_job(
    claimed_id: str,
    worker_id: str,
    sessions: async_sessionmaker[AsyncSession],
    processor: JobProcessor | None,
) -> bool:
    heartbeat_stop = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _heartbeat(sessions, claimed_id, worker_id, heartbeat_stop)
    )
    analyze = processor or _perform_analysis_job
    try:
        async with sessions() as db:
            job = await db.scalar(
                select(ReviewJob).where(
                    ReviewJob.id == claimed_id,
                    ReviewJob.status == "running",
                    ReviewJob.lease_owner == worker_id,
                )
            )
            if not job:
                return False
            result = await asyncio.wait_for(
                analyze(db, job),
                timeout=job.timeout_seconds,
            )
            now = datetime.now(timezone.utc)
            await db.execute(
                update(ReviewJob)
                .where(
                    ReviewJob.id == claimed_id,
                    ReviewJob.status == "running",
                    ReviewJob.lease_owner == worker_id,
                )
                .values(
                    result=result,
                    status="completed",
                    progress=100,
                    stage="Analysis complete",
                    finished_at=now,
                    lease_owner=None,
                    lease_expires_at=None,
                    heartbeat_at=now,
                    error=None,
                )
            )
            await db.commit()
        return True
    except Exception as exc:
        async with sessions() as db:
            await db.rollback()
            job = await db.scalar(
                select(ReviewJob).where(
                    ReviewJob.id == claimed_id,
                    ReviewJob.status == "running",
                    ReviewJob.lease_owner == worker_id,
                )
            )
            if job:
                now = datetime.now(timezone.utc)
                retry = job.attempts < job.max_attempts
                job.status = "queued" if retry else "failed"
                job.stage = "Retry scheduled" if retry else "Analysis failed"
                job.error = (
                    "Analysis timed out."
                    if isinstance(exc, TimeoutError)
                    else f"Analysis attempt failed ({type(exc).__name__})."
                )
                job.finished_at = None if retry else now
                job.lease_owner = None
                job.lease_expires_at = None
                await db.commit()
                logger.warning(
                    "Review job %s failed on attempt %s; retry=%s",
                    claimed_id,
                    job.attempts,
                    retry,
                )
        return True
    finally:
        heartbeat_stop.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


async def process_next_job(
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
    worker_id: str | None = None,
    processor: JobProcessor | None = None,
) -> bool:
    worker_name = worker_id or f"{socket.gethostname()}-{uuid4().hex[:12]}"
    claimed_id = await _claim_job(sessions, worker_name)
    if claimed_id is None:
        return False
    return await _execute_claimed_job(
        claimed_id, worker_name, sessions=sessions, processor=processor
    )


FACT_EXPIRY_INTERVAL = timedelta(hours=24)


async def maybe_run_fact_expiry(
    last_run_at: datetime | None,
    *,
    now: datetime | None = None,
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
    interval: timedelta = FACT_EXPIRY_INTERVAL,
) -> datetime | None:
    """Run fact expiry checks once per configured interval inside the worker loop."""
    current = now or datetime.now(timezone.utc)
    if last_run_at is not None and (current - last_run_at) < interval:
        return last_run_at
    from scripts.expire_facts import process_fact_expiry

    summary = await process_fact_expiry(sessions=sessions, now=current)
    logger.info("Periodic fact expiry completed: %s", summary)
    return current


async def worker_loop() -> None:
    worker_id = f"{socket.gethostname()}-{uuid4().hex[:12]}"
    last_fact_expiry_at: datetime | None = None
    while True:
        try:
            try:
                last_fact_expiry_at = await maybe_run_fact_expiry(last_fact_expiry_at)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Periodic fact expiry failed; continuing review job polling.")
            if not await process_next_job(worker_id=worker_id):
                await asyncio.sleep(settings.job_poll_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Review job worker iteration failed; retrying after poll interval.")
            await asyncio.sleep(settings.job_poll_seconds)


def main() -> None:
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
