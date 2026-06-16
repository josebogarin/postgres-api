from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.crud.user import user_crud
from app.db.session import get_db, get_becbuc_db
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise UnauthorizedError("Invalid token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = int(payload["sub"])  # id es bigint
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Inactive user")
    return user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser access required")
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Acepta admin o superadmin."""
    has_admin = any(r.name in ("admin", "superadmin") for r in current_user.roles)
    if not has_admin:
        raise ForbiddenError("Admin access required")
    return current_user


_bearer_optional = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_optional)] = None,
) -> "User | None":
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        user_id = int(payload["sub"])
        user = await user_crud.get(db, id=user_id)
        return user if (user and user.is_active) else None
    except Exception:
        return None


async def get_current_user_download(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_optional)] = None,
    token_q: str | None = Query(None, alias="token"),
) -> User:
    """Acepta JWT via Authorization header O via ?token= (para descargas iOS/Safari)."""
    token_str = credentials.credentials if credentials else token_q
    if not token_str:
        raise UnauthorizedError("No authentication token provided")
    try:
        payload = decode_token(token_str)
    except ValueError:
        raise UnauthorizedError("Invalid token")
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user_id = int(payload["sub"])
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
OptionalCurrentUser = Annotated["User | None", Depends(get_optional_current_user)]
# Para endpoints de descarga de archivos (soporta ?token= para iOS/Safari)
DownloadUser = Annotated[User, Depends(get_current_user_download)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
BECBUCSession = Annotated[AsyncSession, Depends(get_becbuc_db)]
