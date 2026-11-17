"""Compatibilidade com imports anteriores à divisão dos schemas."""
from .paciente import (PacienteEntrada, PacienteResposta, EventoHistoricoEntrada,
                       EventoHistoricoResposta, HistoricoUnificadoResposta,
                       TriagemEntrada, ResultadoClassificacao, TriagemResposta)
from .item_fila import (ItemFilaCreate, ItemFilaResponse, ItemFilaEntrada, ItemFilaResposta, FilaCreate, FilaResponse)
