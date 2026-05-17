from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal, close_engines
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with AsyncSessionLocal() as session:
        await init_db(session)
        await session.commit()
    yield
    await close_engines()


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)
