from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.queue.motor_priorizacao import AGUARDANDO_VAGA_NA_ESPECIALIDADE


class ItemFilaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    triagem_id: int = Field(..., ge=1, description="ID da triagem realizada", examples=[1])
    paciente_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="ID do paciente triado (opcional, inferido da triagem)",
        examples=[1],
    )
    medico_id: Optional[int] = Field(
        default=None, ge=1, description="ID do médico alocado (opcional)", examples=[1]
    )
    status: str = Field(
        default="aguardando",
        min_length=1,
        max_length=30,
        description="Status do paciente na fila",
        examples=["aguardando"],
    )
    score: float = Field(
        default=0.0,
        ge=0.0,
        description="Pontuação de prioridade para ordenação na fila",
        examples=[100.0],
    )


class ItemFilaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    paciente_nome: Optional[str] = None
    triagem_id: int
    urgencia: Optional[str] = None
    especialidade: Optional[str] = None
    motivo: Optional[str] = None
    status: str = "aguardando"
    score: float = 0.0
    medico_id: Optional[int] = None
    medico_alocado: str = AGUARDANDO_VAGA_NA_ESPECIALIDADE
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_from_orm(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Se já for dicionário, garante medico_alocado caso não tenha vindo
            if "medico_alocado" not in data or data["medico_alocado"] is None:
                data["medico_alocado"] = AGUARDANDO_VAGA_NA_ESPECIALIDADE
            return data

        # Objeto ORM SQLAlchemy
        if hasattr(data, "triagem_id"):
            medico_obj = getattr(data, "medico", None)
            triagem_obj = getattr(data, "triagem", None)
            paciente_obj = getattr(data, "paciente", None)

            medico_nome = (
                medico_obj.nome
                if medico_obj is not None
                else AGUARDANDO_VAGA_NA_ESPECIALIDADE
            )
            motivo = None
            urgencia = None
            especialidade = None
            if triagem_obj is not None:
                motivo = getattr(triagem_obj, "justificativa", None) or getattr(
                    triagem_obj, "texto_sintomas", None
                )
                urgencia = getattr(triagem_obj, "urgencia", None)
                especialidade = getattr(triagem_obj, "especialidade", None)

            paciente_nome = getattr(paciente_obj, "nome", None) if paciente_obj else None

            return {
                "id": getattr(data, "id", None),
                "paciente_id": getattr(data, "paciente_id", None),
                "paciente_nome": paciente_nome,
                "triagem_id": getattr(data, "triagem_id", None),
                "urgencia": urgencia,
                "especialidade": especialidade,
                "motivo": motivo,
                "status": getattr(data, "status", "aguardando"),
                "score": getattr(data, "score", 0.0),
                "medico_id": getattr(data, "medico_id", None),
                "medico_alocado": medico_nome,
                "criado_em": getattr(data, "criado_em", None),
                "atualizado_em": getattr(data, "atualizado_em", None),
            }

        return data


# Aliases para compatibilidade com convenções do projeto
ItemFilaEntrada = ItemFilaCreate
ItemFilaResposta = ItemFilaResponse
FilaCreate = ItemFilaCreate
FilaResponse = ItemFilaResponse
