from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Paciente(Base):
    # Entidade que vai representar os pacientes no banco de dados
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    idade = Column(Integer, nullable=True)
    condicao_cronica = Column(String(200), nullable=True)
    criado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    eventos_historico = relationship(
        "EventoHistorico",  # nome da classe para fazer a relacao
        back_populates="paciente",
        cascade="all, delete-orphan",
        order_by="desc(EventoHistorico.criado_em)"
    )


class EventoHistorico(Base):
    # ENTIDADE PARA O HISTORICO DE CADA PACIENTE
    __tablename__ = "eventos_historico"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_evento = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=False)
    urgencia = Column(String(30), nullable=False, default="baixa") 
    especialidade = Column(String(100), nullable=False, default="clinica_geral")
    justificativa = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    paciente = relationship("Paciente", back_populates="eventos_historico")

