from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.crud.role import role_crud
from app.crud.sistema import sistema_crud
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def create_user(db: AsyncSession, *, user_in: UserCreate) -> User:
    if await user_crud.get_by_email(db, email=str(user_in.email)):
        raise AlreadyExistsError("User with that email")
    if await user_crud.get_by_username(db, username=user_in.username):
        raise AlreadyExistsError("User with that username")
    return await user_crud.create(db, obj_in=user_in)


async def update_user(db: AsyncSession, *, user_id: int, user_in: UserUpdate) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    if user_in.email and str(user_in.email) != user.email:
        if await user_crud.get_by_email(db, email=str(user_in.email)):
            raise AlreadyExistsError("Email")
    if user_in.username and user_in.username != user.username:
        if await user_crud.get_by_username(db, username=user_in.username):
            raise AlreadyExistsError("Username")
    return await user_crud.update(db, db_obj=user, obj_in=user_in)


async def assign_role_to_user(db: AsyncSession, *, user_id: int, role_id: int) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    role = await role_crud.get(db, id=role_id)
    if not role:
        raise NotFoundError("Role")
    return await user_crud.assign_role(db, user=user, role=role)


async def remove_role_from_user(db: AsyncSession, *, user_id: int, role_id: int) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    role = await role_crud.get(db, id=role_id)
    if not role:
        raise NotFoundError("Role")
    return await user_crud.remove_role(db, user=user, role=role)


async def assign_sistema_to_user(db: AsyncSession, *, user_id: int, sistema_id: int) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    sistema = await sistema_crud.get(db, id=sistema_id)
    if not sistema:
        raise NotFoundError("Sistema")
    return await user_crud.assign_sistema(db, user=user, sistema=sistema)


async def remove_sistema_from_user(db: AsyncSession, *, user_id: int, sistema_id: int) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    sistema = await sistema_crud.get(db, id=sistema_id)
    if not sistema:
        raise NotFoundError("Sistema")
    return await user_crud.remove_sistema(db, user=user, sistema=sistema)
