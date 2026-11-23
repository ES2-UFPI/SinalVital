"""Sugestão de encaminhamento no retorno da triagem (issue #69, [005-07], TDD).

POST /pacientes/{id}/triagens devolve `sugestao_fluxo` e `recomendacao`, tanto com o
MockClassificador (MODO_IA=mock) quanto com o ClaudeClassificador (MODO_IA=real).
Nenhum teste acessa a rede: a API da Anthropic é simulada com httpx.MockTransport.
"""

import json

import httpx
import pytest

from app.database.models import Paciente, Triagem
from app.domain.triagem.strategies.classificador import ClassificadorFactory
from app.domain.triagem.strategies.claude_classificador import ClaudeClassificador
from app.triagem.encaminhamento import sugerir_encaminhamento

# relato -> (urgência do MockClassificador, fluxo esperado)
RELATOS_MOCK = {
    "emergencia": ("dor no peito e falta de ar", "urgencia"),
    "alta": ("febre alta e vomitos desde ontem", "urgencia"),
    "media": ("tosse e dor de garganta", "agendamento"),
    "baixa": ("manchas na pele ha uma semana", "agendamento"),
}
FLUXO_POR_URGENCIA = {
    "emergencia": "urgencia",
    "alta": "urgencia",
    "media": "agendamento",
    "baixa": "agendamento",
}


@pytest.fixture(autouse=True)
def modo_mock(monkeypatch):
    monkeypatch.setattr("app.domain.triagem.strategies.classificador.load_dotenv", lambda: None)
    monkeypatch.setenv("MODO_IA", "mock")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture()
def paciente(db_session):
    p = Paciente(nome="Paciente sugestao", email="sugestao@example.com")
    db_session.add(p)
    db_session.commit()
    return p


def triar(client, paciente, relato):
    return client.post(f"/pacientes/{paciente.id}/triagens", json={"relato": relato})


def usar_claude(monkeypatch, handler):
    """Faz a ClassificadorFactory devolver o ClaudeClassificador com a API simulada."""
    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        ClassificadorFactory,
        "criar",
        staticmethod(lambda: ClaudeClassificador(api_key="sk-ant-teste", cliente=cliente)),
    )


def api_devolve(urgencia, especialidade="clinica_geral"):
    corpo = {"urgencia": urgencia, "especialidade": especialidade, "justificativa": "Avaliação simulada."}
    return lambda request: httpx.Response(
        200, json={"content": [{"type": "text", "text": json.dumps(corpo)}]}
    )


# --- MODO_IA=mock --------------------------------------------------------------

@pytest.mark.parametrize("urgencia", list(RELATOS_MOCK))
def test_mock_devolve_sugestao_para_cada_nivel(client, paciente, urgencia):
    relato, fluxo = RELATOS_MOCK[urgencia]

    resposta = triar(client, paciente, relato)

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["urgencia"] == urgencia  # garante que o relato do teste cai no nível esperado
    assert dados["sugestao_fluxo"] == fluxo
    assert dados["recomendacao"] == sugerir_encaminhamento(urgencia)[1]


def test_contratos_anteriores_da_resposta_preservados(client, paciente):
    dados = triar(client, paciente, "dor no peito").json()

    assert dados["classificacao"] == "vermelho"
    assert dados["prioridade"] == 1
    assert dados["urgencia"] == "emergencia"
    assert dados["especialidade"] == "cardiologia"
    assert {"id", "paciente_id", "relato", "estrategia", "justificativa", "criado_em"} <= dados.keys()


def test_sugestao_nao_cria_coluna_nem_altera_o_registro(client, paciente, db_session):
    dados = triar(client, paciente, "dor no peito").json()

    assert "sugestao_fluxo" not in Triagem.__table__.columns
    assert "recomendacao" not in Triagem.__table__.columns

    registro = db_session.get(Triagem, dados["id"])
    assert registro.urgencia == "emergencia"
    # A sugestão é derivada da urgência, então registros antigos também a recebem.
    assert registro.sugestao_fluxo == "urgencia"
    assert registro.recomendacao == dados["recomendacao"]


# --- MODO_IA=real (ClaudeClassificador) ----------------------------------------

@pytest.mark.parametrize("urgencia", ["emergencia", "alta", "media", "baixa"])
def test_claude_devolve_sugestao_para_cada_nivel(client, paciente, monkeypatch, urgencia):
    usar_claude(monkeypatch, api_devolve(urgencia))

    resposta = triar(client, paciente, "relato qualquer de teste")

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["urgencia"] == urgencia
    assert dados["sugestao_fluxo"] == FLUXO_POR_URGENCIA[urgencia]
    assert dados["recomendacao"] == sugerir_encaminhamento(urgencia)[1]


def test_claude_com_falha_na_api_usa_mock_e_ainda_sugere(client, paciente, monkeypatch):
    def falha(request):
        raise httpx.ConnectError("sem rede")

    usar_claude(monkeypatch, falha)

    resposta = triar(client, paciente, "dor no peito e falta de ar")

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["urgencia"] == "emergencia"  # veio do fallback (mock)
    assert dados["sugestao_fluxo"] == "urgencia"
    assert "192" in dados["recomendacao"]


def test_claude_resposta_invalida_usa_mock_e_ainda_sugere(client, paciente, monkeypatch):
    usar_claude(monkeypatch, lambda request: httpx.Response(
        200, json={"content": [{"type": "text", "text": "isto não é JSON"}]}
    ))

    dados = triar(client, paciente, "tosse e dor de garganta").json()

    assert dados["urgencia"] == "media"
    assert dados["sugestao_fluxo"] == "agendamento"
