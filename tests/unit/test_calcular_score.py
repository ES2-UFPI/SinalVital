"""Testes do MotorPriorizacao.calcular_score (issue #43, TDD)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.queue.motor_priorizacao import MotorPriorizacao

AGORA = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def score(urgencia: str, espera_min: float = 0) -> float:
    criado_em = AGORA - timedelta(minutes=espera_min)
    return MotorPriorizacao.calcular_score(urgencia, criado_em, agora=AGORA)


@pytest.mark.parametrize(
    "urgencia, esperado",
    [("emergencia", 100), ("alta", 55), ("media", 30), ("baixa", 10)],
)
def test_espera_zero_retorna_o_peso_da_urgencia(urgencia, esperado):
    assert score(urgencia, 0) == esperado


def test_espera_soma_meio_ponto_por_minuto():
    assert score("baixa", 30) == 25


def test_bonus_de_espera_tem_teto():
    assert score("baixa", 80) == 50
    assert score("baixa", 200) == 50
    assert score("alta", 200) == 95


def test_score_de_caso_leve_cresce_com_a_espera():
    assert score("baixa", 10) < score("baixa", 20) < score("baixa", 60)


def test_alta_recem_chegada_fica_a_frente_de_baixa_que_esperou_muito():
    assert score("alta", 0) > score("baixa", 200)


def test_emergencia_recem_chegada_fica_a_frente_de_alta_que_esperou_muito():
    assert score("emergencia", 0) > score("alta", 200)


def test_media_que_esperou_mais_de_50_min_passa_alta_recem_chegada():
    assert score("media", 60) > score("alta", 0)


def test_urgencia_invalida_levanta_value_error():
    with pytest.raises(ValueError):
        score("critica", 0)


def test_data_sem_fuso_e_tratada_como_utc():
    sem_fuso = (AGORA - timedelta(minutes=30)).replace(tzinfo=None)
    assert MotorPriorizacao.calcular_score("baixa", sem_fuso, agora=AGORA) == 25


def test_criado_em_no_futuro_conta_como_espera_zero():
    futuro = AGORA + timedelta(minutes=10)
    assert MotorPriorizacao.calcular_score("alta", futuro, agora=AGORA) == 55


def test_sem_agora_usa_o_relogio_atual():
    recente = datetime.now(timezone.utc) - timedelta(minutes=10)
    resultado = MotorPriorizacao.calcular_score("baixa", recente)
    assert 14.9 <= resultado <= 15.1
