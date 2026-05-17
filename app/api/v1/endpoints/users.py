import uuid

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentSuperuser, CurrentUser, DBSession
from app.api.permission import require_permission
from app.api.permissions import Perms
from app.core.exceptions import ForbiddenError, NotFoundError
from app.crud.user import user_crud
from app.schemas.user import (
    AssignApplicationRequest,
    AssignRoleRequest,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services import user as user_service

router = APIRouter()


@router.get("/", response_model=list[UserListResponse])
async def list_users(
    db: DBSession,
    _: CurrentSuperuser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    users, _ = await user_crud.get_multi(db, skip=skip, limit=limit)
    return users


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Perms.USER_CREATE))],
)
async def create_user(body: UserCreate, db: DBSession):
    return await user_service.create_user(db, user_in=body)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    if not current_user.is_superuser and current_user.id != user_id:
        raise ForbiddenError()
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID, body: UserUpdate, db: DBSession, current_user: CurrentUser
):
    if not current_user.is_superuser and current_user.id != user_id:
        raise ForbiddenError()
    return await user_service.update_user(db, user_id=user_id, user_in=body)


@router.delete(
    "/{user_id}",
    status_code=204,
    dependencies=[Depends(require_permission(Perms.USER_DELETE))],
)
async def delete_user(user_id: uuid.UUID, db: DBSession):
    await user_crud.delete(db, id=user_id)


@router.post("/{user_id}/roles", response_model=UserResponse)
async def assign_role(user_id: uuid.UUID, body: AssignRoleRequest, db: DBSession, _: CurrentSuperuser):
    return await user_service.assign_role_to_user(db, user_id=user_id, role_id=body.role_id)


@router.delete("/{user_id}/roles/{role_id}", response_model=UserResponse)
async def remove_role(user_id: uuid.UUID, role_id: uuid.UUID, db: DBSession, _: CurrentSuperuser):
    return await user_service.remove_role_from_user(db, user_id=user_id, role_id=role_id)


@router.post("/{user_id}/applications", response_model=UserResponse)
async def assign_application(
    user_id: uuid.UUID, body: AssignApplicationRequest, db: DBSession, _: CurrentSuperuser
):
    return await user_service.assign_application_to_user(
        db, user_id=user_id, application_id=body.application_id
    )
