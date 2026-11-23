from typing import Literal
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .medico import MedicoResposta

DIAS = {'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'}


class MedicoAdminEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    nome: str = Field(min_length=1, max_length=120)
    especialidade: str = Field(min_length=1, max_length=100, pattern=r'^[a-z_]+$')
    tipo_atendimento: Literal['urgencia', 'agendamento', 'ambos'] = 'urgencia'
    capacidade_simultanea: int = Field(default=1, ge=1)
    ativo: bool = True
    dias_atendimento: str | None = Field(default=None, max_length=100)
    limite_diario: int | None = Field(default=None, ge=1)

    @field_validator('especialidade', mode='before')
    @classmethod
    def normalizar_especialidade(cls, valor):
        if not isinstance(valor, str):
            return valor
        texto = unicodedata.normalize('NFKD', valor.strip().lower())
        return '_'.join(''.join(c for c in texto if not unicodedata.combining(c)).split())

    @model_validator(mode='after')
    def validar_agenda(self):
        if self.tipo_atendimento in ('agendamento', 'ambos'):
            if not self.dias_atendimento or self.limite_diario is None:
                raise ValueError('Informe dias de atendimento e limite diário para agendamento.')
            dias = [dia.strip() for dia in self.dias_atendimento.split(',')]
            if any(dia not in DIAS for dia in dias):
                raise ValueError('Selecione dias de atendimento válidos.')
            self.dias_atendimento = ','.join(dict.fromkeys(dias))
        elif self.dias_atendimento is not None or self.limite_diario is not None:
            raise ValueError('Dados de agenda são permitidos somente para agendamento ou ambos.')
        return self


class MedicoAdminResposta(MedicoResposta):
    tipo_atendimento: str
    dias_atendimento: str | None = None
    limite_diario: int | None = None


class AtendimentoAdminResposta(BaseModel):
    id: int
    tipo: Literal['triagem', 'urgencia', 'agendamento', 'consulta']
    etapa: str
    medico_id: int | None = None
    medico_nome: str | None = None
    medico_especialidade: str | None = None
    data: str


class PacienteAdminResposta(BaseModel):
    id: int
    nome: str
    atendimentos: list[AtendimentoAdminResposta]
