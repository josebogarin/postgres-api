from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.auth import Token


async def authenticate(db: AsyncSession, *, username: str, password: str) -> User:
    # Normalizar: username case-insensitive
    username = username.strip().lower()
    user = await user_crud.get_by_username(db, username=username)
    if not user:
        user = await user_crud.get_by_email(db, email=username)
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Usuario o contrasena incorrectos")
    if not user.is_active:
        raise UnauthorizedError("Usuario inactivo")
    return user


def generate_tokens(user: User) -> Token:
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        must_change_password=bool(user.must_change_password),
    )


async def refresh_tokens(db: AsyncSession, *, refresh_token: str) -> Token:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise UnauthorizedError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    user = await user_crud.get(db, id=int(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return generate_tokens(user)
