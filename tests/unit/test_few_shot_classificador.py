"""Testes do few-shot prompting do ClaudeClassificador.

Nenhum teste chama a rede: a API da Anthropic é simulada com httpx.MockTransport.
"""

import json
from pathlib import Path

import httpx
import pytest

from app.domain.triagem.strategies.claude_classificador import (
    ClaudeClassificador,
    _validar,
)
from app.domain.triagem.strategies.exemplos_few_shot import EXEMPLOS
from app.triagem.regras import NIVEIS, ROTULO_ESPECIALIDADE

CHAVE = "sk-ant-chave-de-teste-123"
RELATO = "estou com uma tosse leve há dois dias"
JSON_VALIDO = {
    "urgencia": "baixa",
    "especialidade": "clinica_geral",
    "justificativa": "Tosse leve sem sinais de alerta.",
}
CASOS_AVALIACAO = Path(__file__).resolve().parents[2] / "scripts" / "casos_avaliacao.json"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    monkeypatch.setattr("app.domain.triagem.strategies.classificador.load_dotenv", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("MODO_IA", raising=False)


def corpo_enviado(**opcoes) -> dict:
    """Classifica RELATO com a API simulada e devolve o corpo da requisição."""
    capturados = []

    def handler(request):
        capturados.append(json.loads(request.content))
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": json.dumps(JSON_VALIDO)}]}
        )

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    ClaudeClassificador(api_key=CHAVE, cliente=cliente, **opcoes).classificar(RELATO)
    assert len(capturados) == 1
    return capturados[0]


# --- o que é enviado à API -----------------------------------------------------

def test_por_padrao_envia_os_exemplos_antes_do_relato_real():
    mensagens = corpo_enviado()["messages"]
    assert len(mensagens) == 2 * len(EXEMPLOS) + 1
    assert mensagens[-1] == {"role": "user", "content": f"<relato>{RELATO}</relato>"}


def test_mensagens_alternam_usuario_e_assistente_comecando_pelo_usuario():
    papeis = [m["role"] for m in corpo_enviado()["messages"]]
    assert papeis[0] == "user" and papeis[-1] == "user"
    assert all(a != b for a, b in zip(papeis, papeis[1:]))


def test_cada_exemplo_vira_um_par_relato_e_json():
    mensagens = corpo_enviado()["messages"]
    for i, exemplo in enumerate(EXEMPLOS):
        pergunta, resposta = mensagens[2 * i], mensagens[2 * i + 1]
        assert pergunta == {"role": "user", "content": f"<relato>{exemplo['relato']}</relato>"}
        assert resposta["role"] == "assistant"
        assert json.loads(resposta["content"]) == {
            "urgencia": exemplo["urgencia"],
            "especialidade": exemplo["especialidade"],
            "justificativa": exemplo["justificativa"],
        }


def test_exemplos_vazios_voltam_ao_zero_shot():
    mensagens = corpo_enviado(exemplos=())["messages"]
    assert mensagens == [{"role": "user", "content": f"<relato>{RELATO}</relato>"}]


def test_exemplos_personalizados_substituem_os_padroes():
    proprios = ({"relato": "dor de dente", "urgencia": "media",
                 "especialidade": "clinica_geral", "justificativa": "Dor localizada."},)
    mensagens = corpo_enviado(exemplos=proprios)["messages"]
    assert len(mensagens) == 3
    assert "dor de dente" in mensagens[0]["content"]


def test_o_prompt_de_sistema_nao_muda_com_os_exemplos():
    assert corpo_enviado()["system"] == corpo_enviado(exemplos=())["system"]


# --- qualidade dos exemplos ----------------------------------------------------

@pytest.mark.parametrize("exemplo", EXEMPLOS, ids=lambda e: e["relato"][:40])
def test_cada_exemplo_passa_na_mesma_validacao_da_resposta_real(exemplo):
    resposta = {k: exemplo[k] for k in ("urgencia", "especialidade", "justificativa")}
    assert _validar(resposta) == resposta


def test_exemplos_cobrem_todos_os_niveis_de_urgencia():
    assert {e["urgencia"] for e in EXEMPLOS} == set(NIVEIS)


def test_exemplos_cobrem_todas_as_especialidades():
    assert {e["especialidade"] for e in EXEMPLOS} == set(ROTULO_ESPECIALIDADE)


def test_relatos_dos_exemplos_sao_unicos_e_nao_vazios():
    relatos = [e["relato"].strip() for e in EXEMPLOS]
    assert all(relatos)
    assert len(set(relatos)) == len(relatos)


def test_exemplos_nao_apresentam_diagnostico_fechado():
    # O sistema não faz diagnóstico: a justificativa descreve o critério, não a doença.
    proibidos = ("diagnóstico de", "você tem ", "é um infarto", "é um avc")
    for exemplo in EXEMPLOS:
        assert not any(p in exemplo["justificativa"].lower() for p in proibidos)


def test_ha_exemplo_de_tentativa_de_injecao_de_prompt():
    assert any("ignore" in e["relato"].lower() for e in EXEMPLOS)


def test_ha_exemplo_com_negacao():
    assert any(" não " in f" {e['relato'].lower()} " or " sem " in f" {e['relato'].lower()} "
               for e in EXEMPLOS)


# --- separação entre exemplos e casos de avaliação -----------------------------

def test_nenhum_caso_de_avaliacao_aparece_nos_exemplos():
    """Avaliar com os mesmos casos usados para ensinar inflaria o resultado."""
    casos = json.loads(CASOS_AVALIACAO.read_text(encoding="utf-8"))["casos"]
    de_avaliacao = {c["relato"].strip().lower() for c in casos}
    dos_exemplos = {e["relato"].strip().lower() for e in EXEMPLOS}
    assert de_avaliacao.isdisjoint(dos_exemplos)
