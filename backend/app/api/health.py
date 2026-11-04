from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings
from app.db.session import database_status

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    timestamp: datetime
    database: Literal["connected", "not_configured", "unavailable"]


@router.get("/health", response_model=HealthResponse, summary="Check API and database readiness")
async def health_check() -> HealthResponse:
    db_status = await database_status()
    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
    )
