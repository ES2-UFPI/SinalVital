from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ItemFila(Base):
    __tablename__ = "itens_fila"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    triagem_id: Mapped[int] = mapped_column(
        ForeignKey("triagens.id", ondelete="CASCADE"), index=True, nullable=False
    )
    medico_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("medicos.id", ondelete="SET NULL"), index=True, nullable=True, default=None
    )
    status: Mapped[str] = mapped_column(String(30), default="aguardando", index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    atualizado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    paciente = relationship("Paciente", back_populates="itens_fila")
    triagem = relationship("Triagem", back_populates="item_fila")
    medico = relationship("Medico", back_populates="itens_fila")

