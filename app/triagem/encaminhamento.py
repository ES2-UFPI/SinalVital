"""Sugestão de encaminhamento da triagem (issue #69, [005-07]).

Traduz a urgência classificada (pelo MockClassificador ou pelo ClaudeClassificador) em
um fluxo sugerido e em uma recomendação textual para o paciente:

  emergencia, alta -> "urgencia"
  media, baixa     -> "agendamento"

A regra depende só da urgência, então vale igual para qualquer Classificador e também
para triagens gravadas antes desta issue. É uma orientação de apoio, sem validação
clínica: não faz diagnóstico nem substitui um médico. Os textos devem ser revisados
pelo time/Product Owner.
"""
from typing import Optional, Tuple

FLUXO_URGENCIA = "urgencia"
FLUXO_AGENDAMENTO = "agendamento"

_SUGESTOES = {
    "emergencia": (
        FLUXO_URGENCIA,
        "Procure atendimento de urgência imediatamente ou ligue para o SAMU (192).",
    ),
    "alta": (
        FLUXO_URGENCIA,
        "Procure atendimento de urgência o quanto antes; não espere por uma consulta agendada.",
    ),
    "media": (
        FLUXO_AGENDAMENTO,
        "Agende uma consulta o mais breve possível. "
        "Se os sintomas piorarem, procure atendimento de urgência.",
    ),
    "baixa": (
        FLUXO_AGENDAMENTO,
        "Agende uma consulta de rotina. "
        "Se os sintomas piorarem, procure atendimento de urgência.",
    ),
}

# Urgência ausente ou desconhecida: na dúvida, o fluxo mais seguro (nunca desce de nível).
_SUGESTAO_PADRAO = (
    FLUXO_URGENCIA,
    "Não foi possível definir a urgência com segurança; procure atendimento de urgência.",
)


def sugerir_encaminhamento(urgencia: Optional[str]) -> Tuple[str, str]:
    """Retorna (sugestao_fluxo, recomendacao) para a urgência informada."""
    chave = urgencia.strip().lower() if isinstance(urgencia, str) else ""
    return _SUGESTOES.get(chave, _SUGESTAO_PADRAO)
