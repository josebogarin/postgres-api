from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Detalle(Base):
    __tablename__ = "detalle"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # FK → cabecera.id (la relación con sistema se deriva por cabecera)
    id_cabecera: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cabecera.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relación
    cabecera: Mapped["Cabecera"] = relationship(  # noqa: F821
        "Cabecera", back_populates="detalles"
    )
