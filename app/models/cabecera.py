from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Cabecera(Base):
    __tablename__ = "cabecera"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # FK numérica → sistema.id
    id_sistema: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sistema.id", ondelete="RESTRICT"),
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

    # Relaciones
    sistema: Mapped["Sistema"] = relationship("Sistema")  # noqa: F821
    detalles: Mapped[list["Detalle"]] = relationship(  # noqa: F821
        "Detalle", back_populates="cabecera", cascade="all, delete-orphan"
    )
