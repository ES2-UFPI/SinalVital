from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ItemFilaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    paciente_id: int = Field(..., ge=1, description="ID do paciente triado", examples=[1])
    triagem_id: int = Field(..., ge=1, description="ID da triagem realizada", examples=[1])
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
    triagem_id: int
    medico_id: Optional[int] = None
    status: str
    score: float
    criado_em: datetime
    atualizado_em: Optional[datetime] = None


# Aliases para compatibilidade com convenções do projeto
ItemFilaEntrada = ItemFilaCreate
ItemFilaResposta = ItemFilaResponse

