from datetime import datetime

from pydantic import EmailStr, field_validator

from app.schemas.base import BaseSchema
from app.schemas.role import RoleResponse


class UserBase(BaseSchema):
    username: str
    email: EmailStr
    nombre: str | None = None
    telefono: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    must_change_password: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseSchema):
    username: str = None
    email: EmailStr = None
    nombre: str = None
    telefono: str = None
    is_active: bool = None
    password: str = None
    must_change_password: bool = None


class UserResponse(UserBase):
    id: int
    must_change_password: bool = False
    created_at: datetime = None
    roles: list[RoleResponse] = []

    model_config = {"from_attributes": True}


class UserListResponse(UserBase):
    id: int
    must_change_password: bool = False
    roles: list[RoleResponse] = []

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contrasena debe tener al menos 8 caracteres")
        return v


class AssignRoleRequest(BaseSchema):
    role_id: int


class AssignSistemaRequest(BaseSchema):
    sistema_id: int
