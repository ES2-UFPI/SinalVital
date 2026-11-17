from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ConsultaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    paciente_id: int = Field(..., ge=1)
    medico_id: int = Field(..., ge=1)
    anamnese: Optional[str] = Field(default=None, min_length=1)
    diagnostico: str = Field(..., min_length=1)
    conduta: str = Field(..., min_length=1)


class ConsultaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    medico_id: int
    anamnese: Optional[str] = None
    diagnostico: str
    conduta: str
    criado_em: datetime
