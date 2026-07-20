from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class SistemaBase(BaseSchema):
    nombre: str = Field(..., max_length=255)
    descripcion: str | None = None
    host_bd: str = Field(..., max_length=255)
    puerto_bd: int = Field(5432, ge=1, le=65535)
    nombre_bd: str = Field(..., max_length=100)
    usuario_bd: str = Field(..., max_length=100)
    contrasena_bd: str = Field(..., alias="contraseña_bd", max_length=255)
    es_activo: bool = True

    model_config = {"populate_by_name": True}


class SistemaCreate(SistemaBase):
    pass


class SistemaUpdate(BaseSchema):
    nombre: str | None = Field(None, max_length=255)
    descripcion: str | None = None
    host_bd: str | None = Field(None, max_length=255)
    puerto_bd: int | None = Field(None, ge=1, le=65535)
    nombre_bd: str | None = Field(None, max_length=100)
    usuario_bd: str | None = Field(None, max_length=100)
    contrasena_bd: str | None = Field(None, alias="contraseña_bd", max_length=255)
    es_activo: bool | None = None

    model_config = {"populate_by_name": True}


class SistemaResponse(SistemaBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}
