from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate


class CRUDPermission:
    """CRUD para permissions (PK bigint, no UUID)."""

    async def get(self, db: AsyncSession, *, id: int) -> Permission | None:
        result = await db.execute(select(Permission).where(Permission.id == id))
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Permission | None:
        result = await db.execute(select(Permission).where(Permission.name == name))
        return result.scalar_one_or_none()

    async def get_by_resource_action(
        self, db: AsyncSession, *, resource: str, action: str
    ) -> Permission | None:
        result = await db.execute(
            select(Permission).where(
                (Permission.resource == resource) & (Permission.action == action)
            )
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Permission], int]:
        count_result = await db.execute(select(func.count()).select_from(Permission))
        total = count_result.scalar_one()
        result = await db.execute(
            select(Permission).order_by(Permission.id).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(self, db: AsyncSession, *, obj_in: PermissionCreate) -> Permission:
        obj = Permission(**obj_in.model_dump())
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update(self, db: AsyncSession, *, db_obj: Permission, obj_in: PermissionUpdate) -> Permission:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            if value is not None:
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Permission | None:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj


permission_crud = CRUDPermission()
