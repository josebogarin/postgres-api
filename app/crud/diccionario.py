from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diccionario import Diccionario
from app.schemas.diccionario import DiccionarioCreate, DiccionarioUpdate


class CRUDDiccionario:
    """CRUD operations for Diccionario (field configuration dictionary)."""

    async def get(self, db: AsyncSession, *, id: int) -> Diccionario | None:
        result = await db.execute(select(Diccionario).where(Diccionario.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Diccionario], int]:
        from sqlalchemy import func
        count_result = await db.execute(select(func.count()).select_from(Diccionario))
        total = count_result.scalar_one()
        result = await db.execute(
            select(Diccionario).order_by(Diccionario.id_sistema, Diccionario.campo)
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_by_sistema(
        self, db: AsyncSession, *, id_sistema: int, skip: int = 0, limit: int = 500,
        tabla: str | None = None
    ) -> tuple[list[Diccionario], int]:
        from sqlalchemy import func
        base_q = select(Diccionario).where(Diccionario.id_sistema == id_sistema)
        if tabla is not None:
            base_q = base_q.where(Diccionario.tabla == tabla)
        count_result = await db.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total = count_result.scalar_one()
        result = await db.execute(
            base_q.order_by(Diccionario.tabla, Diccionario.orden_campo, Diccionario.campo)
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_by_campo(
        self, db: AsyncSession, *, campo: str, id_sistema: int | None = None,
        tabla: str | None = None
    ) -> Diccionario | None:
        q = select(Diccionario).where(Diccionario.campo == campo)
        if id_sistema is not None:
            q = q.where(Diccionario.id_sistema == id_sistema)
        if tabla is not None:
            q = q.where(Diccionario.tabla == tabla)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: DiccionarioCreate) -> Diccionario:
        db_obj = Diccionario(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Diccionario, obj_in: DiccionarioUpdate
    ) -> Diccionario:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> None:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()


diccionario_crud = CRUDDiccionario()
