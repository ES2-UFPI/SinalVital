from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    medico_id: Mapped[int] = mapped_column(
        ForeignKey("medicos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    triagem_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("triagens.id", ondelete="SET NULL"), index=True, nullable=True, default=None
    )
    data_agendamento: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    prioridade: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="agendado", index=True)
    recomenda_urgencia: Mapped[bool] = mapped_column(Boolean, default=False)
    justificativa_urgencia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    atualizado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    paciente = relationship("Paciente", back_populates="agendamentos")
    medico = relationship("Medico", back_populates="agendamentos")
    triagem = relationship("Triagem", back_populates="agendamentos")
