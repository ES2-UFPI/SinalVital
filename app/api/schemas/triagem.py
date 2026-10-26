from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TriagemCreate(BaseModel):
    relato: str = Field(..., min_length=5, max_length=5000)
    estrategia: str = "palavras_chave"


class TriagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    relato: str
    estrategia: str
    classificacao: str
    prioridade: int
    urgencia: str
    especialidade: str
    justificativa: str
    criado_em: datetime