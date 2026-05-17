import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        result = await db.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.roles), selectinload(User.applications))
        )
        return result.scalar_one_or_none()

    async def get(self, db: AsyncSession, id: uuid.UUID) -> User | None:
        result = await db.execute(
            select(User)
            .where(User.id == id)
            .options(selectinload(User.roles), selectinload(User.applications))
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        data = obj_in.model_dump(exclude={"password"})
        data["hashed_password"] = hash_password(obj_in.password)
        obj = User(**data)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update_password(self, db: AsyncSession, *, user: User, new_password: str) -> User:
        user.hashed_password = hash_password(new_password)
        db.add(user)
        await db.flush()
        return user

    async def assign_role(self, db: AsyncSession, *, user: User, role: "Role") -> User:  # noqa: F821
        if role not in user.roles:
            user.roles.append(role)
            db.add(user)
            await db.flush()
        return user

    async def remove_role(self, db: AsyncSession, *, user: User, role: "Role") -> User:  # noqa: F821
        if role in user.roles:
            user.roles.remove(role)
            db.add(user)
            await db.flush()
        return user

    async def assign_application(self, db: AsyncSession, *, user: User, application: "Application") -> User:  # noqa: F821
        if application not in user.applications:
            user.applications.append(application)
            db.add(user)
            await db.flush()
        return user

    async def remove_application(self, db: AsyncSession, *, user: User, application: "Application") -> User:  # noqa: F821
        if application in user.applications:
            user.applications.remove(application)
            db.add(user)
            await db.flush()
        return user


user_crud = CRUDUser(User)
