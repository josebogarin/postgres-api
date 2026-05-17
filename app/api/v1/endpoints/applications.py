import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentSuperuser, DBSession
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.crud.application import application_crud
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate

router = APIRouter()


@router.get("/", response_model=list[ApplicationResponse])
async def list_applications(
    db: DBSession,
    _: CurrentSuperuser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    apps, _ = await application_crud.get_multi(db, skip=skip, limit=limit)
    return apps


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def create_application(body: ApplicationCreate, db: DBSession, _: CurrentSuperuser):
    existing = await application_crud.get_by_slug(db, slug=body.slug)
    if existing:
        raise AlreadyExistsError("Application")
    return await application_crud.create(db, obj_in=body)


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: uuid.UUID, db: DBSession, _: CurrentSuperuser):
    app = await application_crud.get(db, id=app_id)
    if not app:
        raise NotFoundError("Application")
    return app


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: uuid.UUID, body: ApplicationUpdate, db: DBSession, _: CurrentSuperuser
):
    app = await application_crud.get(db, id=app_id)
    if not app:
        raise NotFoundError("Application")
    return await application_crud.update(db, db_obj=app, obj_in=body)


@router.delete("/{app_id}", status_code=204)
async def delete_application(app_id: uuid.UUID, db: DBSession, _: CurrentSuperuser):
    await application_crud.delete(db, id=app_id)
