from fastapi import APIRouter, Query

from app.api.deps import CurrentSuperuser, DBSession
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.crud.permission import permission_crud
from app.schemas.permission import PermissionCreate, PermissionResponse, PermissionUpdate

router = APIRouter()


@router.get("/", response_model=list[PermissionResponse])
async def list_permissions(
    db: DBSession,
    _: CurrentSuperuser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all permissions."""
    permissions, _ = await permission_crud.get_multi(db, skip=skip, limit=limit)
    return permissions


@router.post("/", response_model=PermissionResponse, status_code=201)
async def create_permission(
    body: PermissionCreate, db: DBSession, _: CurrentSuperuser
):
    """Create a new permission."""
    existing = await permission_crud.get_by_name(db, name=body.name)
    if existing:
        raise AlreadyExistsError("Permission")
    return await permission_crud.create(db, obj_in=body)


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int, db: DBSession, _: CurrentSuperuser
):
    """Get a specific permission by ID."""
    permission = await permission_crud.get(db, id=permission_id)
    if not permission:
        raise NotFoundError("Permission")
    return permission


@router.patch("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    body: PermissionUpdate,
    db: DBSession,
    _: CurrentSuperuser,
):
    """Update a permission."""
    permission = await permission_crud.get(db, id=permission_id)
    if not permission:
        raise NotFoundError("Permission")
    return await permission_crud.update(db, db_obj=permission, obj_in=body)


@router.delete("/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: int, db: DBSession, _: CurrentSuperuser
):
    """Delete a permission."""
    await permission_crud.delete(db, id=permission_id)
