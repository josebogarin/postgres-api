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
    connect_args={
        "server_settings": {
            # Kill sessions stuck in an open transaction after 60 s
            "idle_in_transaction_session_timeout": "60000",
        }
    },
)

AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

# Public alias used by the generic admin CRUD service
engine = _engine

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
    if _becbuc_engine is not None:
        await _becbuc_engine.dispose()

# ── Engine BECBUC (base becbuc) ──────────────────────────────────────────────
_becbuc_engine = None
_BecbucSessionLocal = None

if settings.DATABASE_BECBUC_URL:
    _becbuc_engine = create_async_engine(
        settings.DATABASE_BECBUC_URL,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _BecbucSessionLocal = async_sessionmaker(_becbuc_engine, expire_on_commit=False)
    logger.info("BECBUC engine registered")

# Alias público para uso en servicios (ej. monitor/scheduler.py)
AsyncBecbucSession = _BecbucSessionLocal

async def get_becbuc_db():
    if _BecbucSessionLocal is None:
        raise RuntimeError("DATABASE_BECBUC_URL no configurada en .env")
    async with _BecbucSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
