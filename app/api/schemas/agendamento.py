from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgendamentoCreate(BaseModel):
    paciente_id: int = Field(..., gt=0, description="ID do paciente")
    medico_id: int = Field(..., gt=0, description="ID do médico")
    data_agendamento: date = Field(..., description="Data da consulta agendada")
    motivo: str = Field(..., min_length=3, description="Motivo do agendamento ou sintomas relatados")
    triagem_id: Optional[int] = Field(None, gt=0, description="ID de triagem prévia (opcional)")
    gestante: Optional[bool] = Field(None, description="Informa se a paciente é gestante")


class AgendamentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    paciente_nome: Optional[str] = None
    paciente_idade: Optional[int] = None
    paciente_condicao_cronica: Optional[str] = None
    paciente_gestante: Optional[bool] = None
    medico_id: int
    medico_nome: Optional[str] = None
    medico_especialidade: Optional[str] = None
    triagem_id: Optional[int] = None
    urgencia: Optional[str] = None
    justificativa_ia: Optional[str] = None
    data_agendamento: date
    motivo: str
    prioridade: float
    status: str
    recomenda_urgencia: bool
    justificativa_urgencia: Optional[str] = None
    criado_em: datetime

    @model_validator(mode="before")
    @classmethod
    def preencher_relacionamentos(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        # Extrai atributos do ORM se presentes
        paciente = getattr(data, "paciente", None)
        medico = getattr(data, "medico", None)
        triagem = getattr(data, "triagem", None)

        paciente_nome = getattr(paciente, "nome", None) if paciente else None
        paciente_idade = getattr(paciente, "idade", None) if paciente else None
        paciente_condicao_cronica = (
            getattr(paciente, "condicao_cronica", None) if paciente else None
        )
        paciente_gestante = getattr(paciente, "gestante", None) if paciente else None
        medico_nome = getattr(medico, "nome", None) if medico else None
        medico_especialidade = getattr(medico, "especialidade", None) if medico else None
        urgencia = (
            getattr(triagem, "urgencia", None) if triagem is not None else "baixa"
        )
        justificativa_ia = (
            getattr(triagem, "justificativa", None)
            if triagem is not None
            else getattr(data, "justificativa_urgencia", None)
        )

        return {
            "id": getattr(data, "id", None),
            "paciente_id": getattr(data, "paciente_id", None),
            "paciente_nome": paciente_nome,
            "paciente_idade": paciente_idade,
            "paciente_condicao_cronica": paciente_condicao_cronica,
            "paciente_gestante": paciente_gestante,
            "medico_id": getattr(data, "medico_id", None),
            "medico_nome": medico_nome,
            "medico_especialidade": medico_especialidade,
            "triagem_id": getattr(data, "triagem_id", None),
            "urgencia": urgencia,
            "justificativa_ia": justificativa_ia,
            "data_agendamento": getattr(data, "data_agendamento", None),
            "motivo": getattr(data, "motivo", None),
            "prioridade": getattr(data, "prioridade", 0.0),
            "status": getattr(data, "status", "agendado"),
            "recomenda_urgencia": getattr(data, "recomenda_urgencia", False),
            "justificativa_urgencia": getattr(data, "justificativa_urgencia", None),
            "criado_em": getattr(data, "criado_em", None),
        }


class DisponibilidadeDiaResponse(BaseModel):
    data: date
    dia_semana: str
    vagas_totais: int
    vagas_ocupadas: int
    vagas_restantes: int
    disponivel: bool


class MedicoAgendamentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    especialidade: str
    dias_atendimento: Optional[str] = None
    limite_diario: Optional[int] = None
