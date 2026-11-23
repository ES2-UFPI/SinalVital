"""Testes da sugestão de encaminhamento da triagem (issue #69, [005-07], TDD).

A regra é pura: urgência -> fluxo sugerido ("urgencia" ou "agendamento") e uma
recomendação textual. Não depende de banco, rede nem de qual Classificador gerou a urgência.
"""

import pytest

from app.triagem.encaminhamento import (
    FLUXO_AGENDAMENTO,
    FLUXO_URGENCIA,
    sugerir_encaminhamento,
)


def test_constantes_do_fluxo():
    assert FLUXO_URGENCIA == "urgencia"
    assert FLUXO_AGENDAMENTO == "agendamento"


@pytest.mark.parametrize("urgencia", ["emergencia", "alta"])
def test_emergencia_e_alta_sugerem_fluxo_de_urgencia(urgencia):
    fluxo, _ = sugerir_encaminhamento(urgencia)
    assert fluxo == "urgencia"


@pytest.mark.parametrize("urgencia", ["media", "baixa"])
def test_media_e_baixa_sugerem_agendamento(urgencia):
    fluxo, _ = sugerir_encaminhamento(urgencia)
    assert fluxo == "agendamento"


@pytest.mark.parametrize("urgencia", ["emergencia", "alta", "media", "baixa"])
def test_recomendacao_textual_nao_vazia(urgencia):
    _, recomendacao = sugerir_encaminhamento(urgencia)
    assert isinstance(recomendacao, str)
    assert recomendacao.strip()


def test_recomendacao_difere_entre_os_niveis():
    recomendacoes = {sugerir_encaminhamento(n)[1] for n in ("emergencia", "alta", "media", "baixa")}
    assert len(recomendacoes) == 4


def test_emergencia_orienta_samu():
    _, recomendacao = sugerir_encaminhamento("emergencia")
    assert "192" in recomendacao


@pytest.mark.parametrize("urgencia", ["media", "baixa"])
def test_agendamento_orienta_procurar_urgencia_se_piorar(urgencia):
    _, recomendacao = sugerir_encaminhamento(urgencia)
    assert "piorar" in recomendacao.lower()


@pytest.mark.parametrize("urgencia", ["EMERGENCIA", " Alta ", "Media", "BAIXA"])
def test_ignora_caixa_e_espacos(urgencia):
    assert sugerir_encaminhamento(urgencia) == sugerir_encaminhamento(urgencia.strip().lower())


@pytest.mark.parametrize("urgencia", [None, "", "desconhecida", "verde"])
def test_urgencia_desconhecida_escala_para_urgencia(urgencia):
    # Na dúvida, o fluxo mais seguro: nunca sugerir agendamento sem urgência conhecida.
    fluxo, recomendacao = sugerir_encaminhamento(urgencia)
    assert fluxo == "urgencia"
    assert recomendacao.strip()
