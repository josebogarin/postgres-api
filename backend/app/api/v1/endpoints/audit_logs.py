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
    user_id: int | None = Query(None, description="Filtrar por ID de usuario"),
    action: str | None = Query(None, description="Filtrar por acción (parcial)"),
    resource: str | None = Query(None, description="Filtrar por recurso"),
):
    logs = await get_audit_logs(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        action=action,
        resource=resource,
    )
    return [
        {
            "id":          log.id,
            "created_at":  log.created_at.isoformat() if log.created_at else None,
            "user_id":     log.user_id,
            "user_email":  log.user_email,
            "action":      log.action,
            "resource":    log.resource,
            "resource_id": log.resource_id,
            "method":      log.method,
            "path":        log.path,
            "status_code": log.status_code,
            "ip_address":  log.ip_address,
            "details":     log.details,
        }
        for log in logs
    ]
