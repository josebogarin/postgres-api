from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Primary engine for user management
_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

# Registry for additional application databases
_app_engines: dict[str, AsyncEngine] = {}
_app_sessions: dict[str, async_sessionmaker] = {}


def _get_or_create_app_engine(app_slug: str) -> AsyncEngine | None:
    if app_slug in _app_engines:
        return _app_engines[app_slug]
    url = settings.APP_DATABASES.get(app_slug)
    if not url:
        return None
    engine = create_async_engine(url, echo=settings.DEBUG, pool_pre_ping=True)
    _app_engines[app_slug] = engine
    _app_sessions[app_slug] = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("Registered app database", app_slug=app_slug)
    return engine


def get_app_session_factory(app_slug: str) -> async_sessionmaker | None:
    _get_or_create_app_engine(app_slug)
    return _app_sessions.get(app_slug)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engines() -> None:
    await _engine.dispose()
    for engine in _app_engines.values():
        await engine.dispose()
