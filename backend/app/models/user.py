from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base
from app.models.permission import user_permissions_direct, user_roles

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.permission import Permission
    from app.models.sistema import Sistema

user_sistemas = Table(
    "user_sistemas",
    Base.metadata,
    Column("user_id",    BigInteger, ForeignKey("users.id",   ondelete="CASCADE"), primary_key=True),
    Column("sistema_id", BigInteger, ForeignKey("sistema.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True)
    telefono: Mapped[str] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=user_roles, lazy="raise"
    )
    direct_permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=user_permissions_direct, lazy="raise"
    )
    sistemas: Mapped[list["Sistema"]] = relationship(
        "Sistema", secondary=user_sistemas, lazy="raise"
    )

    @property
    def is_superuser(self) -> bool:
        return any(r.name == "superadmin" for r in self.roles)
