from app.schemas.base import BaseSchema


class RoleBase(BaseSchema):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseSchema):
    description: str | None = None


class RoleResponse(RoleBase):
    id: int

    model_config = {"from_attributes": True}
