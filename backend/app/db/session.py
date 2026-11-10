from collections.abc import AsyncIterator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
_engine_kwargs: dict = {"pool_pre_ping": True, "pool_recycle": 1800}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"timeout": 30}

engine = create_async_engine(settings.database_url, **_engine_kwargs)
if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def database_status() -> str:
    try:
        from sqlalchemy import text
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "unavailable"
