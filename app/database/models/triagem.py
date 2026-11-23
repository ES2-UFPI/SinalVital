from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base
from app.triagem.encaminhamento import sugerir_encaminhamento


class Triagem(Base):
    __tablename__ = "triagens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), index=True)
    texto_sintomas: Mapped[str] = mapped_column(Text)
    relato = synonym("texto_sintomas")
    urgencia: Mapped[str] = mapped_column(String(30), default="baixa")
    especialidade: Mapped[str] = mapped_column(String(100), default="clinica_geral")
    paciente = relationship("Paciente", back_populates="triagens")
    item_fila = relationship("ItemFila", back_populates="triagem", uselist=False, cascade="all, delete-orphan")
    agendamentos = relationship("Agendamento", back_populates="triagem")
    estrategia: Mapped[str] = mapped_column(String(50), default="palavras_chave")
    classificacao: Mapped[str] = mapped_column(String(20), default="azul")
    prioridade: Mapped[int] = mapped_column(Integer, default=5)
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Derivadas da urgência (issue #69): não são colunas, então não exigem migração
    # e também valem para triagens gravadas antes dessa issue.
    @property
    def sugestao_fluxo(self) -> str:
        return sugerir_encaminhamento(self.urgencia)[0]

    @property
    def recomendacao(self) -> str:
        return sugerir_encaminhamento(self.urgencia)[1]
