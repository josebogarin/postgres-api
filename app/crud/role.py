from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate


class CRUDRole:
    """CRUD para roles (PK bigint, no UUID)."""

    async def get(self, db: AsyncSession, *, id: int) -> Role | None:
        result = await db.execute(select(Role).where(Role.id == id))
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Role | None:
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Role], int]:
        count_result = await db.execute(select(func.count()).select_from(Role))
        total = count_result.scalar_one()
        result = await db.execute(select(Role).order_by(Role.id).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def create(self, db: AsyncSession, *, obj_in: RoleCreate) -> Role:
        obj = Role(**obj_in.model_dump())
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def create_role(self, db: AsyncSession, *, name: str, description: str | None = None) -> Role:
        return await self.create(db, obj_in=RoleCreate(name=name, description=description))

    async def update(self, db: AsyncSession, *, db_obj: Role, obj_in: RoleUpdate) -> Role:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Role | None:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj


role_crud = CRUDRole()
