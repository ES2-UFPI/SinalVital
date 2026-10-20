from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EventoHistoricoEntrada(BaseModel):
    # ESQUEMA PARA CRIACAO DE UM NOVO EVENTO NO HISTORICO
    tipo_evento: str = Field(...,examples=["triagem"])
    descricao: str = Field(..., examples=["Dor no peito e falta de ar ha 30 minutos"])
    urgencia: str = Field(default="baixa", examples=["emergencia"])
    especialidade: str = Field(default="clinica_geral", examples=["cardiologia"])
    justificativa: Optional[str] = Field(None, examples=["Classificado como emergencia por mencionar: dor no peito e falta de ar "])
    
    
class EventoHistoricoResposta(BaseModel):
    # ESQUEMA PARA QUANDO ALGUEM REQUISITAR UMA VISTA DO EVENTO NO HISTORICO
    model_config = ConfigDict(from_attributes=True)
    
    id:int
    paciente_id: int
    tipo_evento: str
    descricao: str
    urgencia: str
    especialidade: str
    justificativa: Optional[str] = None
    criado_em: datetime
    
    
    
class PacienteEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    # ESQUEMA PARA COLOCAR DADOS DE UM PACIENTE NO BANCO DE DADOS
    nome: str = Field(..., min_length=1, max_length=120, examples=["Raimundo"])
    email: EmailStr = Field(..., max_length=120, examples=["raimundo@sinalvital.com"])
    idade:Optional[int] = Field(None, ge=0, examples=[65])
    condicao_cronica: Optional[str] = Field(None, max_length=200, examples=["Cardiopatia e hipertensao"])

class PacienteResposta(BaseModel):
    # ESQUEMA DE GET PARA VISUALIZAR OS DADOS DO PACIENTE
    model_config=ConfigDict(from_attributes=True)
    
    id: int
    nome:str
    email:str
    idade:Optional[int] = None
    condicao_cronica: Optional[str] = None
    criado_em: datetime
    
class HistoricoUnificadoResposta(PacienteResposta):
    #ESQUEMA CASO ALGUEM REQUISITE UM GET PARA VISUALIZAR pacientes/{id}/historico
    model_config = ConfigDict(from_attributes=True)
    eventos_historico:list[EventoHistoricoResposta] = []
