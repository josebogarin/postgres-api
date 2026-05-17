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


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = await user_crud.get_by_email(db, email=email)
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedError("Inactive user")
    return user


def generate_tokens(user: User) -> Token:
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


async def refresh_tokens(db: AsyncSession, *, refresh_token: str) -> Token:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise UnauthorizedError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    user = await user_crud.get(db, id=payload["sub"])
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return generate_tokens(user)
