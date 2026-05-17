from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class ApplicationBase(BaseSchema):
    slug: str
    name: str
    description: str | None = None
    is_active: bool = True


class ApplicationCreate(ApplicationBase):
    db_url: str | None = None


class ApplicationUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    db_url: str | None = None
    is_active: bool | None = None


class ApplicationResponse(ApplicationBase, UUIDSchema, TimestampSchema):
    pass
