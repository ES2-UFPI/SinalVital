from pydantic import BaseModel, ConfigDict


class MedicoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    crm: str
    especialidade: str
