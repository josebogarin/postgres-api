from datetime import datetime

from app.schemas.base import BaseSchema


class DiccionarioBase(BaseSchema):
    tabla: str | None = None
    campo: str
    alias: str | None = None
    descripcion: str | None = None
    tipo_dato: str | None = None
    es_visible: bool | None = True
    es_solo_lectura: bool | None = False
    es_obligatorio: bool | None = False
    orden_campo: int | None = None
    decimales: int | None = None
    texto_ayuda: str | None = None
    valor_defecto: str | None = None
    multivalor: str | None = None
    grupo: int | None = 0
    calculo: str | None = None
    id_sistema: int | None = None


class DiccionarioCreate(DiccionarioBase):
    pass


class DiccionarioUpdate(BaseSchema):
    tabla: str | None = None
    campo: str | None = None
    alias: str | None = None
    descripcion: str | None = None
    tipo_dato: str | None = None
    es_visible: bool | None = None
    es_solo_lectura: bool | None = None
    es_obligatorio: bool | None = None
    orden_campo: int | None = None
    decimales: int | None = None
    texto_ayuda: str | None = None
    valor_defecto: str | None = None
    multivalor: str | None = None
    grupo: int | None = None
    calculo: str | None = None
    id_sistema: int | None = None


class DiccionarioResponse(DiccionarioBase):
    id: int
    crear_en: datetime | None = None
    actualizar_en: datetime | None = None

    model_config = {"from_attributes": True}
