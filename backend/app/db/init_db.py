from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.role import role_crud
from app.crud.user import user_crud
from app.models.role import RoleEnum
from app.schemas.user import UserCreate

logger = get_logger(__name__)


async def init_db(session: AsyncSession) -> None:
    # Sembrar roles base
    for role_name in RoleEnum:
        existing = await role_crud.get_by_name(session, name=role_name.value)
        if not existing:
            await role_crud.create_role(session, name=role_name.value)
            logger.info("Created role", role=role_name.value)

    # Sembrar superusuario
    superuser = await user_crud.get_by_email(session, email=settings.FIRST_SUPERUSER_EMAIL)
    if not superuser:
        # Derivar username del email (parte antes del @)
        username = settings.FIRST_SUPERUSER_EMAIL.split("@")[0]
        user_in = UserCreate(
            username=username,
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
        )
        superuser = await user_crud.create(session, obj_in=user_in)
        logger.info("Superuser created", email=settings.FIRST_SUPERUSER_EMAIL)

    # Asignar rol superadmin si no lo tiene
    # Usamos SQL directo para evitar conflictos de lazy="selectin" + selectinload
    # que ocurren cuando hay objetos Role en la sesión al mismo tiempo que se
    # accede a la colección roles del usuario.
    superadmin_role = await role_crud.get_by_name(session, name=RoleEnum.superadmin.value)
    if superadmin_role:
        from sqlalchemy import text as _text
        already = await session.execute(
            _text("SELECT COUNT(*) FROM user_roles WHERE user_id = :uid AND role_id = :rid"),
            {"uid": superuser.id, "rid": superadmin_role.id},
        )
        if (already.scalar() or 0) == 0:
            await session.execute(
                _text("INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"),
                {"uid": superuser.id, "rid": superadmin_role.id},
            )
            logger.info("Superadmin role assigned", email=settings.FIRST_SUPERUSER_EMAIL)
