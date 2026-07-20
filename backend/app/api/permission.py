from typing import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, get_current_user
from app.core.exceptions import ForbiddenError
from app.models.role import Role
from app.models.user import User


def require_permission(perm: str) -> Callable:
    async def _check(
        db: DBSession,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        # Reload user with roles and their permissions eagerly
        result = await db.execute(
            select(User)
            .where(User.id == current_user.id)
            .options(
                selectinload(User.roles).selectinload(Role.permissions)
            )
        )
        user_with_perms = result.scalar_one_or_none()
        if user_with_perms is None:
            raise ForbiddenError(f"Permission '{perm}' required")

        for role in user_with_perms.roles:
            for permission in role.permissions:
                if permission.name == perm:
                    return current_user

        raise ForbiddenError(f"Permission '{perm}' required")

    return _check
