from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser:

    async def _get_with_relations(self, db: AsyncSession, stmt):
        result = await db.execute(
            stmt.options(
                selectinload(User.roles),
                selectinload(User.direct_permissions),
                selectinload(User.sistemas),
            )
        )
        return result.scalar_one_or_none()

    async def get(self, db: AsyncSession, *, id: int):
        return await self._get_with_relations(db, select(User).where(User.id == id))

    async def get_by_email(self, db: AsyncSession, *, email: str):
        return await self._get_with_relations(db, select(User).where(User.email == email))

    async def get_by_username(self, db: AsyncSession, *, username: str):
        return await self._get_with_relations(
            db, select(User).where(User.username == username.strip().lower())
        )

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100):
        from sqlalchemy import func
        count_result = await db.execute(select(func.count()).select_from(User))
        total = count_result.scalar_one()
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.roles),
                selectinload(User.direct_permissions),
                selectinload(User.sistemas),
            )
            .order_by(User.id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(self, db: AsyncSession, *, obj_in: UserCreate):
        username = obj_in.username.strip().lower()
        obj = User(
            username=username,
            email=str(obj_in.email),
            nombre=obj_in.nombre or username,
            telefono=obj_in.telefono,
            password_hash=hash_password(obj_in.password),
            is_active=obj_in.is_active,
            must_change_password=obj_in.must_change_password,
        )
        db.add(obj)
        await db.flush()
        return await self._get_with_relations(db, select(User).where(User.id == obj.id))

    async def update(self, db: AsyncSession, *, db_obj: User, obj_in):
        data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        if "password" in data:
            data["password_hash"] = hash_password(data.pop("password"))
        for field, value in data.items():
            if value is not None:
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        return await self._get_with_relations(db, select(User).where(User.id == db_obj.id))

    async def update_password(self, db: AsyncSession, *, user: User, new_password: str):
        user.password_hash = hash_password(new_password)
        db.add(user)
        await db.flush()
        return user

    async def delete(self, db: AsyncSession, *, id: int):
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj

    async def assign_role(self, db: AsyncSession, *, user: User, role):
        roles_list = user.roles if isinstance(user.roles, list) else []
        if role not in roles_list:
            if isinstance(user.roles, list):
                user.roles.append(role)
            db.add(user)
            await db.flush()
        return user

    async def remove_role(self, db: AsyncSession, *, user: User, role):
        roles_list = user.roles if isinstance(user.roles, list) else []
        if role in roles_list:
            user.roles.remove(role)
            db.add(user)
            await db.flush()
        return user

    async def assign_sistema(self, db: AsyncSession, *, user: User, sistema):
        if sistema not in user.sistemas:
            user.sistemas.append(sistema)
            db.add(user)
            await db.flush()
        return user

    async def remove_sistema(self, db: AsyncSession, *, user: User, sistema):
        if sistema in user.sistemas:
            user.sistemas.remove(sistema)
            db.add(user)
            await db.flush()
        return user


user_crud = CRUDUser()
