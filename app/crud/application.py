from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate


class CRUDApplication(CRUDBase[Application, ApplicationCreate, ApplicationUpdate]):
    async def get_by_slug(self, db: AsyncSession, *, slug: str) -> Application | None:
        result = await db.execute(select(Application).where(Application.slug == slug))
        return result.scalar_one_or_none()


application_crud = CRUDApplication(Application)
