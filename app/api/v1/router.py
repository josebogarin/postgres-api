from fastapi import APIRouter

from app.api.v1.endpoints import applications, audit_logs, auth, health, roles, users

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
