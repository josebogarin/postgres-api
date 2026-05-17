import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentSuperuser, DBSession
from app.crud.audit_log import get_audit_logs

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    db: DBSession,
    _: CurrentSuperuser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
):
    return await get_audit_logs(db, skip=skip, limit=limit, user_id=user_id, action=action)
