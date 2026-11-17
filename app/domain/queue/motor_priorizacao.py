"""Motor de priorização da fila (Sprint 2): score por urgência e escolha de médico."""

from datetime import datetime, timezone
from typing import Mapping, Optional, Protocol, Sequence

PESO_URGENCIA = {"emergencia": 100, "alta": 55, "media": 30, "baixa": 10}
BONUS_POR_MINUTO = 0.5
BONUS_MAXIMO = 40.0
AGUARDANDO_VAGA_NA_ESPECIALIDADE = "Aguardando vaga na especialidade"


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
        """Seleciona médico ativo da especialidade, com vaga e menor carga.

        Cargas são contagens não negativas por ID; IDs ausentes contam como zero.
        Empates são resolvidos pelo menor ID. Não modifica os argumentos nem
        reserva vaga. Sem candidato, retorna None: a integração da fila deve
        apresentar AGUARDANDO_VAGA_NA_ESPECIALIDADE (issue #44).
        """
        disponiveis = (
            medico for medico in medicos
            if medico.ativo
            and medico.especialidade == especialidade
            and carga_atual.get(medico.id, 0) < medico.capacidade_simultanea
        )
        return min(
            disponiveis,
            key=lambda medico: (carga_atual.get(medico.id, 0), medico.id),
            default=None,
        )
