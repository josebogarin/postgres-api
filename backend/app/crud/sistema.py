from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sistema import Sistema
from app.schemas.sistema import SistemaCreate, SistemaUpdate


class CRUDSistema:
    """CRUD para la tabla sistema (PK bigint)."""

    async def get(self, db: AsyncSession, *, id: int) -> Sistema | None:
        result = await db.execute(select(Sistema).where(Sistema.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Sistema], int]:
        count_result = await db.execute(select(func.count()).select_from(Sistema))
        total = count_result.scalar_one()
        result = await db.execute(
            select(Sistema).order_by(Sistema.id).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_activos(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Sistema], int]:
        count_result = await db.execute(
            select(func.count()).select_from(Sistema).where(Sistema.es_activo == True)  # noqa: E712
        )
        total = count_result.scalar_one()
        result = await db.execute(
            select(Sistema).where(Sistema.es_activo == True)  # noqa: E712
            .order_by(Sistema.id).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(self, db: AsyncSession, *, obj_in: SistemaCreate) -> Sistema:
        data = obj_in.model_dump(by_alias=False)
        obj = Sistema(**data)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update(
        self, db: AsyncSession, *, db_obj: Sistema, obj_in: SistemaUpdate
    ) -> Sistema:
        data = obj_in.model_dump(exclude_unset=True, by_alias=False)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Sistema | None:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj


sistema_crud = CRUDSistema()
