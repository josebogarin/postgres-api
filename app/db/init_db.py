from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.role import role_crud
from app.crud.user import user_crud
from app.models.role import RoleEnum
from app.schemas.user import UserCreate

logger = get_logger(__name__)


async def init_db(session: AsyncSession) -> None:
    # Seed base roles
    for role_name in RoleEnum:
        existing = await role_crud.get_by_name(session, name=role_name.value)
        if not existing:
            await role_crud.create_role(session, name=role_name.value)
            logger.info("Created role", role=role_name.value)

    # Seed superuser
    superuser = await user_crud.get_by_email(session, email=settings.FIRST_SUPERUSER_EMAIL)
    if not superuser:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            full_name="Super Admin",
            is_superuser=True,
        )
        await user_crud.create(session, obj_in=user_in)
        logger.info("Superuser created", email=settings.FIRST_SUPERUSER_EMAIL)
