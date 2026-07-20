from app.schemas.base import BaseSchema


class PermissionBase(BaseSchema):
    name: str
    description: str | None = None


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None


class PermissionResponse(PermissionBase):
    id: int

    model_config = {"from_attributes": True}
