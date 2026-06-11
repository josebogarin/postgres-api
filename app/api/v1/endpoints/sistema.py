from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentSuperuser, CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.crud.sistema import sistema_crud
from app.schemas.sistema import SistemaCreate, SistemaResponse, SistemaUpdate

router = APIRouter()


class SistemaPublico(BaseModel):
    id: int
    nombre: str
    class Config:
        from_attributes = True


@router.get("/publico", response_model=list[SistemaPublico])
async def list_sistemas_publico(db: DBSession):
    """Endpoint público — solo id+nombre, sin credenciales. Para el formulario de login."""
    items, _ = await sistema_crud.get_activos(db, skip=0, limit=500)
    return items


@router.get("/", response_model=list[SistemaResponse])
async def list_sistemas(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Superadmin: devuelve todos los sistemas activos.
    Otros usuarios: devuelve solo los sistemas asignados.
    """
    if current_user.is_superuser:
        items, _ = await sistema_crud.get_activos(db, skip=skip, limit=limit)
    else:
        # Devolver solo los sistemas que el usuario tiene asignados y están activos
        items = [s for s in current_user.sistemas if s.es_activo]
        items = items[skip: skip + limit]
    return items


@router.get("/activos", response_model=list[SistemaResponse])
async def list_sistemas_activos(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Igual que GET / — sistemas activos según permisos del usuario."""
    if current_user.is_superuser:
        items, _ = await sistema_crud.get_activos(db, skip=skip, limit=limit)
    else:
        items = [s for s in current_user.sistemas if s.es_activo]
        items = items[skip: skip + limit]
    return items


@router.post("/", response_model=SistemaResponse, status_code=201)
async def create_sistema(body: SistemaCreate, db: DBSession, _: CurrentSuperuser):
    return await sistema_crud.create(db, obj_in=body)


@router.get("/{sistema_id}", response_model=SistemaResponse)
async def get_sistema(sistema_id: int, db: DBSession, current_user: CurrentUser):
    item = await sistema_crud.get(db, id=sistema_id)
    if not item:
        raise NotFoundError("Sistema")
    # Verificar acceso
    if not current_user.is_superuser:
        if sistema_id not in {s.id for s in current_user.sistemas}:
            raise NotFoundError("Sistema")
    return item


@router.patch("/{sistema_id}", response_model=SistemaResponse)
async def update_sistema(
    sistema_id: int, body: SistemaUpdate, db: DBSession, _: CurrentSuperuser
):
    item = await sistema_crud.get(db, id=sistema_id)
    if not item:
        raise NotFoundError("Sistema")
    return await sistema_crud.update(db, db_obj=item, obj_in=body)


@router.delete("/{sistema_id}", status_code=204)
async def delete_sistema(sistema_id: int, db: DBSession, _: CurrentSuperuser):
    item = await sistema_crud.get(db, id=sistema_id)
    if not item:
        raise NotFoundError("Sistema")
    await sistema_crud.delete(db, id=sistema_id)
