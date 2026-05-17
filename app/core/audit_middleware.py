import base64
import json
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_AUDITED_METHODS = {"POST", "PATCH", "DELETE"}
_AUDIT_PREFIX = "/api/v1/"


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        decoded = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded)
    except Exception:
        return {}


def _get_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _path_to_resource(path: str) -> str:
    """Derive a resource name from a URL path."""
    # e.g. /api/v1/users/123 -> "users"
    try:
        after_prefix = path.split("/api/v1/", 1)[1]
        segment = after_prefix.split("/")[0]
        return segment or path
    except (IndexError, ValueError):
        return path


def _method_to_action(method: str, resource: str) -> str:
    mapping = {
        "POST": f"{resource}:create",
        "PATCH": f"{resource}:update",
        "DELETE": f"{resource}:delete",
    }
    return mapping.get(method, f"{resource}:{method.lower()}")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method not in _AUDITED_METHODS:
            return response

        path = request.url.path
        if not path.startswith(_AUDIT_PREFIX):
            return response

        # Extract user info from JWT without signature validation
        user_id: uuid.UUID | None = None
        user_email: str | None = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            payload = _decode_jwt_payload(token)
            raw_sub = payload.get("sub")
            if raw_sub:
                try:
                    user_id = uuid.UUID(raw_sub)
                except ValueError:
                    pass
            user_email = payload.get("email")

        resource = _path_to_resource(path)
        action = _method_to_action(request.method, resource)
        ip = _get_ip(request)
        status_code = response.status_code

        try:
            async with AsyncSessionLocal() as db:
                from app.models.audit_log import AuditLog

                entry = AuditLog(
                    user_id=user_id,
                    user_email=user_email,
                    action=action,
                    resource=resource,
                    method=request.method,
                    path=path,
                    status_code=status_code,
                    ip_address=ip,
                    details=None,
                )
                db.add(entry)
                await db.commit()
        except Exception:
            logger.exception("Failed to write audit log entry")

        return response
