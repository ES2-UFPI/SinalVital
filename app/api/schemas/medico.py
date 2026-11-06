from pydantic import BaseModel, ConfigDict


class MedicoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    especialidade: str
    capacidade_simultanea: int
    ativo: bool
