from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Diccionario(Base):
    """
    Diccionario de campos — configuración de campos para formularios/vistas.
    Cada entrada pertenece a un sistema específico (FK → sistema.id).
    """
    __tablename__ = "diccionario"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    id_sistema: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sistema.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tabla: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    campo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_dato: Mapped[str | None] = mapped_column(String(100), nullable=True)
    es_visible: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    es_solo_lectura: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    es_obligatorio: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    orden_campo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decimales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    texto_ayuda: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_defecto: Mapped[str | None] = mapped_column(Text, nullable=True)
    multivalor: Mapped[str | None] = mapped_column(Text, nullable=True)
    grupo: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    calculo: Mapped[str | None] = mapped_column(String(50), nullable=True)

    crear_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=True
    )
    actualizar_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Relación con sistema — noload para evitar lazy-load en contexto async
    sistema: Mapped["Sistema | None"] = relationship("Sistema", lazy="noload")  # noqa: F821
