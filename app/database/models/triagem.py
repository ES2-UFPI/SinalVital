from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base


class Triagem(Base):
    __tablename__ = "triagens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), index=True)
    texto_sintomas: Mapped[str] = mapped_column(Text)
    relato = synonym("texto_sintomas")
    urgencia: Mapped[str] = mapped_column(String(30), default="baixa")
    especialidade: Mapped[str] = mapped_column(String(100), default="clinica_geral")
    paciente = relationship("Paciente", back_populates="triagens")
    estrategia: Mapped[str] = mapped_column(String(50), default="palavras_chave")
    classificacao: Mapped[str] = mapped_column(String(20), default="azul")
    prioridade: Mapped[int] = mapped_column(Integer, default=5)
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
