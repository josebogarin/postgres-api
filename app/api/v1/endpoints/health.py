from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DBSession

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/db")
async def db_health(db: DBSession):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
