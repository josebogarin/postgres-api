from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import AlreadyExistsError, ForbiddenError, NotFoundError
from app.crud.diccionario import diccionario_crud
from app.models.user import User
from app.schemas.diccionario import DiccionarioCreate, DiccionarioResponse, DiccionarioUpdate

router = APIRouter()


def _require_edit(user: User, id_sistema: int | None) -> None:
    """Superadmin siempre puede. Admin solo si tiene el sistema asignado."""
    if user.is_superuser:
        return
    if not any(r.name == "admin" for r in user.roles):
        raise ForbiddenError("Se requiere rol admin o superadmin para editar el diccionario")
    if id_sistema is not None:
        if id_sistema not in {s.id for s in user.sistemas}:
            raise ForbiddenError("Sin acceso al sistema seleccionado")


@router.get("/", response_model=list[DiccionarioResponse])
async def list_diccionario(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    id_sistema: int | None = Query(None, description="Filtrar por sistema"),
    tabla: str | None = Query(None, description="Filtrar por tabla"),
):
    """Lista entradas del diccionario. Superadmin ve todo; otros solo sus sistemas."""
    if not current_user.is_superuser and id_sistema is not None:
        if id_sistema not in {s.id for s in current_user.sistemas}:
            return []

    if id_sistema is not None:
        entries, _ = await diccionario_crud.get_by_sistema(
            db, id_sistema=id_sistema, skip=skip, limit=limit, tabla=tabla
        )
    else:
        entries, _ = await diccionario_crud.get_multi(db, skip=skip, limit=limit)
    return entries


@router.post("/", response_model=DiccionarioResponse, status_code=201)
async def create_diccionario(
    body: DiccionarioCreate, db: DBSession, current_user: CurrentUser
):
    """Crea una nueva entrada en el diccionario."""
    _require_edit(current_user, body.id_sistema)
    existing = await diccionario_crud.get_by_campo(
        db, campo=body.campo, id_sistema=body.id_sistema, tabla=body.tabla
    )
    if existing:
        raise AlreadyExistsError("Ya existe una entrada para este campo en el sistema")
    return await diccionario_crud.create(db, obj_in=body)


@router.get("/{entry_id}", response_model=DiccionarioResponse)
async def get_diccionario(entry_id: int, db: DBSession, current_user: CurrentUser):
    """Obtiene una entrada del diccionario por ID."""
    entry = await diccionario_crud.get(db, id=entry_id)
    if not entry:
        raise NotFoundError("Diccionario")
    return entry


@router.patch("/{entry_id}", response_model=DiccionarioResponse)
async def update_diccionario(
    entry_id: int, body: DiccionarioUpdate, db: DBSession, current_user: CurrentUser
):
    """Actualiza una entrada del diccionario."""
    entry = await diccionario_crud.get(db, id=entry_id)
    if not entry:
        raise NotFoundError("Diccionario")
    _require_edit(current_user, entry.id_sistema)
    return await diccionario_crud.update(db, db_obj=entry, obj_in=body)


@router.delete("/{entry_id}", status_code=204)
async def delete_diccionario(entry_id: int, db: DBSession, current_user: CurrentUser):
    """Elimina una entrada del diccionario."""
    entry = await diccionario_crud.get(db, id=entry_id)
    if not entry:
        raise NotFoundError("Diccionario")
    _require_edit(current_user, entry.id_sistema)
    await diccionario_crud.delete(db, id=entry_id)
