from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import UnauthorizedError
from app.crud.audit_log import log_action
from app.schemas.auth import LoginRequest, RefreshRequest, Token
from app.schemas.user import UserResponse
from app.services import auth as auth_service

router = APIRouter()


def _get_ip(request: Request) -> str | None:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: DBSession, request: Request):
    ip = _get_ip(request)
    try:
        user   = await auth_service.authenticate(db, username=body.username, password=body.password)
        tokens = auth_service.generate_tokens(user)

        # Auditar login exitoso con datos completos del usuario
        await log_action(
            db,
            user=user,
            action="auth:login",
            resource="auth",
            method="POST",
            path="/api/v1/auth/login",
            status_code=200,
            ip=ip,
            details={"username": body.username, "result": "success"},
        )
        await db.commit()
        return tokens

    except UnauthorizedError:
        # Auditar intento de login fallido
        try:
            await log_action(
                db,
                user=None,
                action="auth:login_failed",
                resource="auth",
                method="POST",
                path="/api/v1/auth/login",
                status_code=401,
                ip=ip,
                details={"username": body.username, "result": "failed"},
            )
            await db.commit()
        except Exception:
            pass
        raise


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest, db: DBSession):
    return await auth_service.refresh_tokens(db, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    import logging
    log = logging.getLogger("auth.me")
    log.info(f"[ME] user={current_user.username} id={current_user.id}")
    log.info(f"[ME] roles type={type(current_user.roles)!r} value={current_user.roles!r}")
    log.info(f"[ME] nombre={current_user.nombre!r} telefono={current_user.telefono!r}")
    try:
        roles_list = list(current_user.roles) if current_user.roles is not None else []
        log.info(f"[ME] roles_list={roles_list}")
        result = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "nombre": current_user.nombre,
            "telefono": current_user.telefono,
            "is_active": current_user.is_active,
            "must_change_password": bool(current_user.must_change_password),
            "created_at": current_user.created_at,
            "roles": [
                {"id": r.id, "name": r.name, "description": r.description}
                for r in roles_list
            ],
        }
        log.info(f"[ME] result dict OK, roles count={len(result['roles'])}")
        return result
    except Exception as e:
        log.error(f"[ME] ERROR: {type(e).__name__}: {e}", exc_info=True)
        raise
