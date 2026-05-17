from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Role | None:
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def create_role(self, db: AsyncSession, *, name: str, description: str | None = None) -> Role:
        return await self.create(db, obj_in=RoleCreate(name=name, description=description))


role_crud = CRUDRole(Role)
