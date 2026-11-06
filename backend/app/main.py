from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.core.config import settings
from app.db.session import engine
from app.api.auth import router as auth_router
from app.api.knowledge import router as knowledge_router
from app.api.workspace import router as workspace_router
from app.api.content import router as content_router
from app.api.workflow import router as workflow_router
from app.api.intelligence import router as intelligence_router
from app.api.release import router as release_router
from app.api.notifications import router as notifications_router
from app.api.insights import router as insights_router
from app.db.base import Base
import app.models.entities  # Register ORM models before migrations/tests


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if engine is not None:
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="BrandCourt API: foundation, brand knowledge, content analysis, image intelligence, reporting and review workflow.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(workspace_router, prefix=settings.api_prefix)
app.include_router(content_router, prefix=settings.api_prefix)
app.include_router(workflow_router, prefix=settings.api_prefix)
app.include_router(intelligence_router, prefix=settings.api_prefix)
app.include_router(release_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)
app.include_router(insights_router, prefix=settings.api_prefix)


@app.get("/", tags=["root"], summary="API landing endpoint")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": f"{settings.api_prefix}/health"}
