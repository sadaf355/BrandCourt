from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import ContentItem, ContentRevision, ReviewJob, User


async def enqueue_review_job(
    db: AsyncSession,
    user: User,
    item: ContentItem,
    revision: ContentRevision,
) -> ReviewJob:
    job = ReviewJob(
        workspace_id=user.workspace_id,
        content_id=item.id,
        revision_id=revision.id,
        created_by=user.id,
        status="queued",
        progress=0,
        stage="Queued",
        max_attempts=settings.job_max_attempts,
        timeout_seconds=settings.job_timeout_seconds,
    )
    db.add(job)
    await db.flush()
    return job
