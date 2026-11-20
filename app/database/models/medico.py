from datetime import date
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base

DIAS_SEMANA_MAPA = {
    0: ("segunda", "segunda-feira", "seg", "mon", "monday"),
    1: ("terca", "terca-feira", "terça", "terça-feira", "ter", "tue", "tuesday"),
    2: ("quarta", "quarta-feira", "qua", "wed", "wednesday"),
    3: ("quinta", "quinta-feira", "qui", "thu", "thursday"),
    4: ("sexta", "sexta-feira", "sex", "fri", "friday"),
    5: ("sabado", "sábado", "sab", "sat", "saturday"),
    6: ("domingo", "dom", "sun", "sunday"),
}


class Medico(Base):
    __tablename__ = "medicos"
    __table_args__ = (
        CheckConstraint("capacidade_simultanea > 0", name="ck_medicos_capacidade_positiva"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    especialidade = Column(String(100), nullable=False)
    capacidade_simultanea = Column(Integer, nullable=False, default=1)
    ativo = Column(Boolean, nullable=False, default=True)

    # Diferenciação entre médicos de urgência e consultas agendadas
    tipo_atendimento = Column(String(30), nullable=False, default="urgencia")  # "urgencia", "agendamento", "ambos"
    dias_atendimento = Column(String(100), nullable=True)  # ex.: "segunda,quarta,sexta"
    limite_diario = Column(Integer, nullable=True)  # Limite diário de pacientes agendados

    itens_fila = relationship("ItemFila", back_populates="medico")
    agendamentos = relationship("Agendamento", back_populates="medico")

    def atende_agendamento(self) -> bool:
        return self.tipo_atendimento in ("agendamento", "ambos")

    def atende_em_dia(self, data_alvo: date) -> bool:
        """Verifica se o médico atende consultas agendadas no dia da semana da data informada."""
        if not self.atende_agendamento():
            return False
        if not self.dias_atendimento:
            return True  # Sem restrição de dias se não configurado
        
        weekday = data_alvo.weekday()
        termos_dia = DIAS_SEMANA_MAPA.get(weekday, ())
        
        dias_cadastrados = [d.strip().lower() for d in self.dias_atendimento.split(",") if d.strip()]
        for dia in dias_cadastrados:
            if any(termo in dia or dia in termo for termo in termos_dia):
                return True
        return False
