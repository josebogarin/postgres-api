import uuid

from pydantic import EmailStr, field_validator

from app.schemas.application import ApplicationResponse
from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema
from app.schemas.role import RoleResponse


class UserBase(BaseSchema):
    email: EmailStr
    full_name: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    is_superuser: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseSchema):
    full_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(UserBase, UUIDSchema, TimestampSchema):
    is_superuser: bool
    is_verified: bool
    roles: list[RoleResponse] = []
    applications: list[ApplicationResponse] = []


class UserListResponse(UserBase, UUIDSchema):
    is_superuser: bool
    is_verified: bool


class AssignRoleRequest(BaseSchema):
    role_id: uuid.UUID


class AssignApplicationRequest(BaseSchema):
    application_id: uuid.UUID
