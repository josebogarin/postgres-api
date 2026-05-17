import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentSuperuser, DBSession
from app.core.exceptions import NotFoundError
from app.crud.role import role_crud
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter()


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    db: DBSession,
    _: CurrentSuperuser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    roles, _ = await role_crud.get_multi(db, skip=skip, limit=limit)
    return roles


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(body: RoleCreate, db: DBSession, _: CurrentSuperuser):
    return await role_crud.create(db, obj_in=body)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(role_id: uuid.UUID, body: RoleUpdate, db: DBSession, _: CurrentSuperuser):
    role = await role_crud.get(db, id=role_id)
    if not role:
        raise NotFoundError("Role")
    return await role_crud.update(db, db_obj=role, obj_in=body)


@router.delete("/{role_id}", status_code=204)
async def delete_role(role_id: uuid.UUID, db: DBSession, _: CurrentSuperuser):
    await role_crud.delete(db, id=role_id)
