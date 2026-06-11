from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    apostador_bets,
    audit_logs,
    auth,
    database_admin,
    diccionario,
    health,
    monitor,
    permissions,
    portal,
    roles,
    sistema,
    torneo,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(sistema.router, prefix="/sistema", tags=["sistema"])
api_router.include_router(diccionario.router, prefix="/diccionario", tags=["diccionario"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(database_admin.router, prefix="/admin/db", tags=["database-admin"])
api_router.include_router(portal.router, prefix="/portal", tags=["portal"])
api_router.include_router(torneo.router, prefix="/torneo", tags=["torneo"])
api_router.include_router(apostador_bets.router, prefix="/bets", tags=["apuestas"])
api_router.include_router(monitor.router, prefix="/monitor", tags=["monitor"])
