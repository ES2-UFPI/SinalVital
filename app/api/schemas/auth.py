from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class LoginEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    perfil: Literal["paciente", "medico"]
    identificador: str = Field(min_length=1, max_length=120)


class PerfilResposta(BaseModel):
    perfil: Literal["paciente", "medico"]
    id: int
    nome: str
