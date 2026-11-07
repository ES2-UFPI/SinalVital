"""Motor de priorização da fila (Sprint 2): score por urgência e escolha de médico."""

from datetime import datetime, timezone
from typing import Mapping, Optional, Protocol, Sequence

PESO_URGENCIA = {"emergencia": 100, "alta": 55, "media": 30, "baixa": 10}
BONUS_POR_MINUTO = 0.5
BONUS_MAXIMO = 40.0


class MedicoLike(Protocol):
    """O que o motor precisa de um médico (o modelo real vem da issue #40)."""

    id: int
    especialidade: str
    capacidade_simultanea: int
    ativo: bool


def _como_utc(momento: datetime) -> datetime:
    """Trata data sem fuso horário como UTC (o SQLite pode devolver assim)."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


class MotorPriorizacao:
    @staticmethod
    def calcular_score(
        urgencia: str, criado_em: datetime, agora: Optional[datetime] = None
    ) -> float:
        """Peso da urgência + bônus de espera (0,5 por minuto, com teto).

        Maior score = atendido primeiro. Urgência fora das quatro conhecidas
        levanta ValueError; espera negativa conta como zero.
        """
        if urgencia not in PESO_URGENCIA:
            raise ValueError(
                f"Urgência inválida: {urgencia!r}. Use {', '.join(PESO_URGENCIA)}."
            )
        referencia = _como_utc(agora) if agora is not None else datetime.now(timezone.utc)
        minutos = max((referencia - _como_utc(criado_em)).total_seconds() / 60, 0.0)
        bonus = min(minutos * BONUS_POR_MINUTO, BONUS_MAXIMO)
        return PESO_URGENCIA[urgencia] + bonus

    @staticmethod
    def escolher_medico(
        especialidade: str,
        medicos: Sequence[MedicoLike],
        carga_atual: Mapping[int, int],
    ) -> Optional[MedicoLike]:
        """Issue #41 (Pablo). Implementar com TDD. Sem vaga, devolve None."""
        raise NotImplementedError
