"""
Testes unitários para o cálculo de prioridade fixa da fila de consultas agendadas.
Critérios de prioridade fixa:
- Idade (>= 80 superidoso, >= 60 idoso, <= 5 primeira infância)
- Gravidez / gestante
- Condição crônica
- Urgência clínica da triagem (se houver)
- Prioridade fixa SEM evolução temporal (não aumenta com o passar do tempo).
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.domain.agendamento.priorizacao import calcular_prioridade_agendamento


def test_prioridade_fixa_sem_tempo_de_espera():
    """Garante que a prioridade de agendamento não varia com o passar do tempo."""
    agora = datetime.now(timezone.utc)
    passado = agora - timedelta(days=10)

    score_recente = calcular_prioridade_agendamento(
        idade=40,
        gestante=False,
        condicao_cronica=None,
        urgencia="baixa",
        criado_em=agora,
    )
    score_antigo = calcular_prioridade_agendamento(
        idade=40,
        gestante=False,
        condicao_cronica=None,
        urgencia="baixa",
        criado_em=passado,
    )

    # Ambas devem ser rigorosamente iguais, sem bônus de tempo
    assert score_recente == score_antigo


def test_prioridade_fixa_fatores_cumulativos():
    """Testa a ponderação por idade, gravidez, condição crônica e urgência."""
    # Paciente jovem sem condições
    score_base = calcular_prioridade_agendamento(
        idade=25,
        gestante=False,
        condicao_cronica=None,
        urgencia="baixa",
    )

    # Idoso (>= 60) tem prioridade maior que jovem
    score_idoso = calcular_prioridade_agendamento(
        idade=65,
        gestante=False,
        condicao_cronica=None,
        urgencia="baixa",
    )
    assert score_idoso > score_base

    # Superidoso (>= 80) tem prioridade maior que idoso
    score_superidoso = calcular_prioridade_agendamento(
        idade=82,
        gestante=False,
        condicao_cronica=None,
        urgencia="baixa",
    )
    assert score_superidoso > score_idoso

    # Gestante tem acréscimo de prioridade
    score_gestante = calcular_prioridade_agendamento(
        idade=25,
        gestante=True,
        condicao_cronica=None,
        urgencia="baixa",
    )
    assert score_gestante > score_base

    # Condição crônica acrescenta prioridade
    score_cronico = calcular_prioridade_agendamento(
        idade=25,
        gestante=False,
        condicao_cronica="Diabetes tipo 2",
        urgencia="baixa",
    )
    assert score_cronico > score_base

    # Caso cumulativo: idosa, gestante, condição crônica e urgência alta
    score_combinado = calcular_prioridade_agendamento(
        idade=62,
        gestante=True,
        condicao_cronica="Hipertensão",
        urgencia="alta",
    )
    assert score_combinado > score_gestante
    assert score_combinado > score_cronico
    assert score_combinado > score_idoso
