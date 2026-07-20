from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Sistema(Base, TimestampMixin):
    __tablename__ = "sistema"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    host_bd: Mapped[str] = mapped_column(String(255), nullable=False)
    puerto_bd: Mapped[int] = mapped_column(Integer, default=5432, nullable=False)
    nombre_bd: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario_bd: Mapped[str] = mapped_column(String(100), nullable=False)
    contrasena_bd: Mapped[str] = mapped_column("contraseña_bd", String(255), nullable=False)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
