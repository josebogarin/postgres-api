from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentSuperuser, CurrentUser, DBSession
from app.api.permission import require_permission
from app.api.permissions import Perms
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.crud.user import user_crud
from app.schemas.user import (
    AssignRoleRequest,
    AssignSistemaRequest,
    ChangePasswordRequest,
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


@router.post("/me/change-password", status_code=204)
async def change_password(body: ChangePasswordRequest, db: DBSession, current_user: CurrentUser):
    """Cambia la contraseña del usuario autenticado.
    La comparación es case-insensitive (todo se normaliza a minúsculas).
    """
    if not verify_password(body.current_password, current_user.password_hash):
        raise UnauthorizedError("Contraseña actual incorrecta")
    new_hash = hash_password(body.new_password)
    from sqlalchemy import text as _text
    await db.execute(
        _text("UPDATE users SET password_hash = :h, must_change_password = FALSE WHERE id = :id"),
        {"h": new_hash, "id": current_user.id},
    )
    await db.commit()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: DBSession, current_user: CurrentUser):
    if not current_user.is_superuser and current_user.id != user_id:
        raise ForbiddenError()
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, body: UserUpdate, db: DBSession, current_user: CurrentUser
):
    if not current_user.is_superuser and current_user.id != user_id:
        raise ForbiddenError()
    return await user_service.update_user(db, user_id=user_id, user_in=body)


@router.delete(
    "/{user_id}",
    status_code=204,
    dependencies=[Depends(require_permission(Perms.USER_DELETE))],
)
async def delete_user(user_id: int, db: DBSession):
    await user_crud.delete(db, id=user_id)


@router.post("/{user_id}/roles", response_model=UserResponse)
async def assign_role(user_id: int, body: AssignRoleRequest, db: DBSession, _: CurrentSuperuser):
    return await user_service.assign_role_to_user(db, user_id=user_id, role_id=body.role_id)


@router.delete("/{user_id}/roles/{role_id}", response_model=UserResponse)
async def remove_role(user_id: int, role_id: int, db: DBSession, _: CurrentSuperuser):
    return await user_service.remove_role_from_user(db, user_id=user_id, role_id=role_id)


@router.get("/{user_id}/sistemas", response_model=list[dict])
async def get_user_sistemas(user_id: int, db: DBSession, _: CurrentSuperuser):
    """Lista los sistemas asignados a un usuario."""
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundError("User")
    return [{"id": s.id, "nombre": s.nombre, "nombre_bd": s.nombre_bd} for s in user.sistemas]


@router.post("/{user_id}/sistemas", response_model=UserResponse)
async def assign_sistema(
    user_id: int, body: AssignSistemaRequest, db: DBSession, _: CurrentSuperuser
):
    """Asigna acceso a un sistema para un usuario."""
    return await user_service.assign_sistema_to_user(
        db, user_id=user_id, sistema_id=body.sistema_id
    )


@router.delete("/{user_id}/sistemas/{sistema_id}", response_model=UserResponse)
async def remove_sistema(user_id: int, sistema_id: int, db: DBSession, _: CurrentSuperuser):
    """Quita el acceso a un sistema de un usuario."""
    return