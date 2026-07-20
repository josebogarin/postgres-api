"""
Middleware de auditoría ASGI puro.
- Registra POST / PUT / PATCH / DELETE sobre /api/v1/
- Login y login fallido se registran desde el endpoint de auth (no aquí)
- Extrae user_id (int) del JWT y busca email en BD
- Extrae resource_id numérico del path
"""
import base64
import json
import logging

from sqlalchemy import text
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_AUDIT_PREFIX    = "/api/v1/"

# Paths que el middleware omite (gestionados directamente en el endpoint)
_SKIP_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


def _get_ip(request: Request) -> str | None:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _path_to_resource(path: str) -> str:
    try:
        after = path.split("/api/v1/", 1)[1]
        return after.split("/")[0] or path
    except (IndexError, ValueError):
        return path


def _extract_resource_id(path: str) -> str | None:
    """Extrae el ID numérico del path, p.ej. /api/v1/diccionario/42 → '42'."""
    for part in reversed(path.rstrip("/").split("/")):
        if part.isdigit():
            return part
    return None


def _method_to_action(method: str, resource: str) -> str:
    return {
        "POST":   f"{resource}:create",
        "PUT":    f"{resource}:replace",
        "PATCH":  f"{resource}:update",
        "DELETE": f"{resource}:delete",
    }.get(method, f"{resource}:{method.lower()}")


class AuditMiddleware:
    """Pure ASGI middleware — no BaseHTTPMiddleware para no interferir con
    el cleanup de dependencias de FastAPI."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request    = Request(scope, receive)
        method     = request.method
        path       = request.url.path
        should_audit = (
            method in _AUDITED_METHODS
            and path.startswith(_AUDIT_PREFIX)
            and path not in _SKIP_PATHS
        )

        status_code = 500

        async def send_wrapper(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper if should_audit else send)

        if not should_audit:
            return

        # ── Identificar usuario desde JWT ─────────────────────────────────
        user_id:    int | None = None
        user_email: str | None = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            payload = _decode_jwt_payload(auth_header[len("Bearer "):])
            raw_sub = payload.get("sub")
            if raw_sub:
                try:
                    user_id = int(raw_sub)
                except (ValueError, TypeError):
                    pass

        # Email no está en el JWT — buscarlo en BD por user_id
        if user_id is not None:
            try:
                async with AsyncSessionLocal() as lookup_db:
                    row = (await lookup_db.execute(
                        text("SELECT email FROM users WHERE id = :id"),
                        {"id": user_id},
                    )).fetchone()
                    if row:
                        user_email = row[0]
            except Exception:
                pass

        resource    = _path_to_resource(path)
        resource_id = _extract_resource_id(path)
        action      = _method_to_action(method, resource)
        ip          = _get_ip(request)

        try:
            async with AsyncSessionLocal() as db:
                from app.models.audit_log import AuditLog
                db.add(AuditLog(
                    user_id=user_id,
                    user_email=user_email,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    ip_address=ip,
                    details=None,
                ))
                await db.commit()
        except Exception:
            logger.exception("Failed to write audit log entry")
