import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.crud.application import application_crud
from app.crud.role import role_crud
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def create_user(db: AsyncSession, *, user_in: UserCreate) -> User:
    existing = await user_crud.get_by_email(db, email=user_in.email)
    if existing:
        raise AlreadyExistsError("User")
    return await user_crud.create(db, obj_in=user_in)


async def update_user(db: AsyncSession, *, user_id: uuid.UUID, user_in: UserUpdate) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    if user_in.email and user_in.email != user.email:
        if await user_crud.get_by_email(db, email=user_in.email):
            raise AlreadyExistsError("Email")
    if user_in.password:
        await user_crud.update_password(db, user=user, new_password=user_in.password)
    data = user_in.model_dump(exclude_unset=True, exclude={"password"})
    return await user_crud.update(db, db_obj=user, obj_in=data)


async def assign_role_to_user(db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    role = await role_crud.get(db, id=role_id)
    if not role:
        raise NotFoundError("Role")
    return await user_crud.assign_role(db, user=user, role=role)


async def remove_role_from_user(db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    role = await role_crud.get(db, id=role_id)
    if not role:
        raise NotFoundError("Role")
    return await user_crud.remove_role(db, user=user, role=role)


async def assign_application_to_user(
    db: AsyncSession, *, user_id: uuid.UUID, application_id: uuid.UUID
) -> User:
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    app = await application_crud.get(db, id=application_id)
    if not app:
        raise NotFoundError("Application")
    return await user_crud.assign_application(db, user=user, application=app)
