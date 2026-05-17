from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class RoleBase(BaseSchema):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseSchema):
    description: str | None = None


class RoleResponse(RoleBase, UUIDSchema, TimestampSchema):
    pass
