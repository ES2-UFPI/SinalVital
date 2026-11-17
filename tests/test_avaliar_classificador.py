"""Testes do script de avaliação (scripts/avaliar_classificador.py).

Usam classificadores falsos: nenhum teste chama a rede nem gasta crédito.
"""

import json
from pathlib import Path

import pytest

from app.domain.triagem.strategies.classificador import Classificador
from scripts.avaliar_classificador import avaliar, carregar_casos

CASOS = [
    {"relato": "a", "urgencia": "emergencia", "especialidade": "cardiologia"},
    {"relato": "b", "urgencia": "alta", "especialidade": "clinica_geral"},
    {"relato": "c", "urgencia": "baixa", "especialidade": "dermatologia"},
]


class Roteirizado(Classificador):
    """Devolve respostas pré-definidas por relato (ou levanta o erro indicado)."""

    def __init__(self, respostas: dict):
        self.respostas = respostas

    def classificar(self, texto_sintomas: str):
        resposta = self.respostas[texto_sintomas]
        if isinstance(resposta, Exception):
            raise resposta
        return {"urgencia": resposta[0], "especialidade": resposta[1], "justificativa": "x"}


def test_tudo_certo_da_cem_por_cento():
    gabarito = {c["relato"]: (c["urgencia"], c["especialidade"]) for c in CASOS}
    r = avaliar(Roteirizado(gabarito), CASOS)
    assert r["total"] == 3
    assert r["acertos_urgencia"] == r["acertos_especialidade"] == r["acertos_total"] == 3
    assert r["subtriagem"] == 0 and r["erros"] == 0 and r["divergencias"] == []


def test_conta_urgencia_e_especialidade_separadamente():
    respostas = {
        "a": ("emergencia", "clinica_geral"),   # urgência certa, especialidade errada
        "b": ("media", "clinica_geral"),        # urgência errada, especialidade certa
        "c": ("baixa", "dermatologia"),         # tudo certo
    }
    r = avaliar(Roteirizado(respostas), CASOS)
    assert r["acertos_urgencia"] == 2
    assert r["acertos_especialidade"] == 2
    assert r["acertos_total"] == 1
    assert len(r["divergencias"]) == 2


def test_subtriagem_so_conta_quando_o_modelo_subestima_a_urgencia():
    respostas = {
        "a": ("alta", "cardiologia"),           # esperado emergência: SUBESTIMOU
        "b": ("emergencia", "clinica_geral"),   # esperado alta: superestimou (menos grave)
        "c": ("baixa", "dermatologia"),
    }
    r = avaliar(Roteirizado(respostas), CASOS)
    assert r["subtriagem"] == 1
    assert r["supertriagem"] == 1


def test_falha_do_classificador_conta_como_erro_e_nao_interrompe():
    respostas = {
        "a": RuntimeError("API indisponível"),
        "b": ("alta", "clinica_geral"),
        "c": ("baixa", "dermatologia"),
    }
    r = avaliar(Roteirizado(respostas), CASOS)
    assert r["erros"] == 1
    assert r["acertos_total"] == 2
    assert r["subtriagem"] == 0


def test_casos_do_repositorio_sao_validos():
    casos = carregar_casos()
    assert len(casos) >= 20
    from app.triagem.regras import NIVEIS, ROTULO_ESPECIALIDADE
    for caso in casos:
        assert caso["relato"].strip()
        assert caso["urgencia"] in NIVEIS
        assert caso["especialidade"] in ROTULO_ESPECIALIDADE
    assert {c["urgencia"] for c in casos} == set(NIVEIS)
    assert len({c["relato"] for c in casos}) == len(casos)


def test_arquivo_de_casos_avisa_que_o_gabarito_precisa_de_revisao():
    bruto = json.loads(
        (Path(__file__).resolve().parents[1] / "scripts" / "casos_avaliacao.json")
        .read_text(encoding="utf-8")
    )
    assert "revis" in bruto["aviso"].lower()
