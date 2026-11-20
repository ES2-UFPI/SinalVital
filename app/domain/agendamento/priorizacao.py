"""
Cálculo de prioridade fixa para a fila de consultas agendadas.
Critérios fixos (sem evolução temporal):
- Urgência clínica (se houver triagem): emergencia=100, alta=55, media=30, baixa=10
- Idade: >= 80 anos (+30 pts), >= 60 anos (+20 pts), <= 5 anos (+15 pts)
- Gestante: +30 pts
- Condição crônica: +20 pts
"""

from datetime import datetime
from typing import Optional

PESOS_URGENCIA_FIXA = {
    "emergencia": 100.0,
    "alta": 55.0,
    "media": 30.0,
    "baixa": 10.0,
}


def calcular_prioridade_agendamento(
    idade: Optional[int] = None,
    gestante: bool = False,
    condicao_cronica: Optional[str] = None,
    urgencia: Optional[str] = "baixa",
    criado_em: Optional[datetime] = None,
) -> float:
    """
    Calcula o score de prioridade fixa do paciente para consultas agendadas.
    O resultado é determinístico e NÃO evolui com o passar do tempo (criado_em é ignorado).
    """
    score = 0.0

    # 1. Urgência clínica de base
    urg = (urgencia or "baixa").lower().strip()
    score += PESOS_URGENCIA_FIXA.get(urg, 10.0)

    # 2. Idade
    if idade is not None:
        if idade >= 80:
            score += 30.0
        elif idade >= 60:
            score += 20.0
        elif idade <= 5:
            score += 15.0

    # 3. Gestante
    if gestante:
        score += 30.0

    # 4. Condição crônica presente
    if condicao_cronica and condicao_cronica.strip():
        score += 20.0

    return score
