"""Testes do ClaudeClassificador (issue #48, TDD).

Nenhum teste chama a rede: a API da Anthropic é simulada com httpx.MockTransport.
"""

import json
import logging

import httpx
import pytest

from app.domain.triagem.strategies.classificador import (
    Classificador,
    ClassificadorFactory,
    MockClassificador,
)
from app.domain.triagem.strategies.claude_classificador import ClaudeClassificador

CHAVE = "sk-ant-chave-de-teste-123"
RELATO = "dor no peito e falta de ar"
JSON_VALIDO = {
    "urgencia": "emergencia",
    "especialidade": "cardiologia",
    "justificativa": "Dor no peito com falta de ar sugere quadro cardíaco agudo.",
}


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    # O .env do desenvolvedor não pode interferir nos testes.
    monkeypatch.setattr("app.domain.triagem.strategies.classificador.load_dotenv", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("MODO_IA", raising=False)


def resposta_api(texto: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"content": [{"type": "text", "text": texto}]})


def classificador_com(handler, chave: str | None = CHAVE) -> ClaudeClassificador:
    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    return ClaudeClassificador(api_key=chave, cliente=cliente)


def sempre(resposta: httpx.Response):
    return lambda request: resposta


def levanta(erro: Exception):
    def handler(request):
        raise erro
    return handler


def resultado_do_mock(texto: str = RELATO) -> dict:
    return MockClassificador().classificar(texto)


# --- contrato e resposta válida ------------------------------------------------

def test_implementa_a_interface_classificador():
    assert isinstance(ClaudeClassificador(api_key=CHAVE), Classificador)


def test_resposta_valida_vira_resultado_de_classificacao():
    classificador = classificador_com(sempre(resposta_api(json.dumps(JSON_VALIDO))))
    assert classificador.classificar(RELATO) == JSON_VALIDO


def test_extrai_json_de_bloco_de_codigo_markdown():
    texto = "```json\n" + json.dumps(JSON_VALIDO) + "\n```"
    classificador = classificador_com(sempre(resposta_api(texto)))
    assert classificador.classificar(RELATO) == JSON_VALIDO


def test_extrai_json_cercado_de_texto():
    texto = "Claro! Segue a classificação:\n" + json.dumps(JSON_VALIDO) + "\nEspero ter ajudado."
    classificador = classificador_com(sempre(resposta_api(texto)))
    assert classificador.classificar(RELATO) == JSON_VALIDO


def test_normaliza_caixa_e_espacos_dos_valores():
    bruto = {**JSON_VALIDO, "urgencia": " ALTA ", "especialidade": "Cardiologia"}
    classificador = classificador_com(sempre(resposta_api(json.dumps(bruto))))
    resultado = classificador.classificar(RELATO)
    assert resultado["urgencia"] == "alta"
    assert resultado["especialidade"] == "cardiologia"


# --- requisição enviada à API --------------------------------------------------

def test_requisicao_usa_endpoint_chave_modelo_e_relato():
    capturadas = []

    def handler(request):
        capturadas.append(request)
        return resposta_api(json.dumps(JSON_VALIDO))

    classificador_com(handler).classificar(RELATO)

    assert len(capturadas) == 1
    request = capturadas[0]
    corpo = json.loads(request.content)
    assert request.method == "POST"
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == CHAVE
    assert request.headers["anthropic-version"]
    assert corpo["model"]
    assert corpo["max_tokens"] > 0
    assert RELATO in json.dumps(corpo["messages"], ensure_ascii=False)
    assert CHAVE not in request.content.decode()


def test_prompt_pede_json_estruturado_com_os_valores_permitidos():
    capturadas = []

    def handler(request):
        capturadas.append(json.loads(request.content))
        return resposta_api(json.dumps(JSON_VALIDO))

    classificador_com(handler).classificar(RELATO)
    prompt = json.dumps(capturadas[0], ensure_ascii=False)
    for valor in ("emergencia", "alta", "media", "baixa", "cardiologia",
                  "oftalmologia", "dermatologia", "clinica_geral", "justificativa", "JSON"):
        assert valor in prompt


def test_define_timeout_na_requisicao():
    capturadas = []

    def handler(request):
        capturadas.append(request.extensions["timeout"])
        return resposta_api(json.dumps(JSON_VALIDO))

    classificador_com(handler).classificar(RELATO)
    assert 0 < capturadas[0]["read"] <= 30


def test_modelo_pode_ser_configurado_por_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "modelo-de-teste")
    capturadas = []

    def handler(request):
        capturadas.append(json.loads(request.content))
        return resposta_api(json.dumps(JSON_VALIDO))

    classificador_com(handler).classificar(RELATO)
    assert capturadas[0]["model"] == "modelo-de-teste"


def test_chave_vem_da_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-do-ambiente")
    capturadas = []

    def handler(request):
        capturadas.append(request.headers["x-api-key"])
        return resposta_api(json.dumps(JSON_VALIDO))

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    ClaudeClassificador(cliente=cliente).classificar(RELATO)
    assert capturadas == ["chave-do-ambiente"]


# --- fallback seguro -----------------------------------------------------------

@pytest.mark.parametrize("handler", [
    sempre(httpx.Response(500, json={"error": "indisponivel"})),
    sempre(httpx.Response(401, json={"error": "chave invalida"})),
    sempre(httpx.Response(429, json={"error": "limite"})),
    levanta(httpx.ReadTimeout("tempo esgotado")),
    levanta(httpx.ConnectError("sem rede")),
], ids=["http-500", "http-401", "http-429", "timeout", "falha-de-rede"])
def test_falha_de_rede_ou_http_usa_o_mock(handler):
    classificador = classificador_com(handler)
    assert classificador.classificar(RELATO) == resultado_do_mock()


@pytest.mark.parametrize("texto", [
    "isto não é json",
    "",
    "[1, 2, 3]",
    json.dumps({"urgencia": "alta"}),
    json.dumps({**JSON_VALIDO, "urgencia": "critica"}),
    json.dumps({**JSON_VALIDO, "especialidade": "neurologia"}),
    json.dumps({**JSON_VALIDO, "justificativa": ""}),
    json.dumps({**JSON_VALIDO, "urgencia": 3}),
], ids=["texto-livre", "vazio", "lista", "campos-faltando", "urgencia-invalida",
        "especialidade-invalida", "justificativa-vazia", "urgencia-nao-texto"])
def test_resposta_invalida_usa_o_mock(texto):
    classificador = classificador_com(sempre(resposta_api(texto)))
    assert classificador.classificar(RELATO) == resultado_do_mock()


def test_corpo_da_resposta_inesperado_usa_o_mock():
    classificador = classificador_com(sempre(httpx.Response(200, json={"foo": "bar"})))
    assert classificador.classificar(RELATO) == resultado_do_mock()


def test_fallback_registra_o_erro_sem_vazar_chave_nem_relato(caplog):
    classificador = classificador_com(sempre(httpx.Response(500, json={})))
    with caplog.at_level(logging.WARNING):
        classificador.classificar(RELATO)
    assert caplog.records, "o erro deve ser registrado em log"
    texto_do_log = caplog.text
    assert CHAVE not in texto_do_log
    assert RELATO not in texto_do_log


def test_sem_chave_nao_chama_a_api_e_usa_o_mock(caplog):
    chamadas = []

    def handler(request):
        chamadas.append(request)
        return resposta_api(json.dumps(JSON_VALIDO))

    classificador = classificador_com(handler, chave=None)
    with caplog.at_level(logging.WARNING):
        resultado = classificador.classificar(RELATO)

    assert chamadas == []
    assert resultado == resultado_do_mock()
    assert "ANTHROPIC_API_KEY" in caplog.text


def test_relato_vazio_levanta_value_error_sem_chamar_a_api():
    chamadas = []

    def handler(request):
        chamadas.append(request)
        return resposta_api(json.dumps(JSON_VALIDO))

    classificador = classificador_com(handler)
    with pytest.raises(ValueError):
        classificador.classificar("   ")
    assert chamadas == []


# --- ClassificadorFactory ------------------------------------------------------

def test_factory_em_modo_real_instancia_o_claude_classificador(monkeypatch):
    monkeypatch.setenv("MODO_IA", "real")
    assert isinstance(ClassificadorFactory.criar(), ClaudeClassificador)


def test_factory_em_modo_real_aceita_caixa_e_espacos(monkeypatch):
    monkeypatch.setenv("MODO_IA", " REAL ")
    assert isinstance(ClassificadorFactory.criar(), ClaudeClassificador)


def test_factory_em_modo_real_sem_chave_continua_funcionando(monkeypatch):
    monkeypatch.setenv("MODO_IA", "real")
    resultado = ClassificadorFactory.criar().classificar(RELATO)
    assert resultado == resultado_do_mock()


@pytest.mark.parametrize("modo", [None, "mock", " MOCK "])
def test_factory_em_modo_mock_ou_padrao_continua_usando_o_mock(monkeypatch, modo):
    if modo is None:
        monkeypatch.delenv("MODO_IA", raising=False)
    else:
        monkeypatch.setenv("MODO_IA", modo)
    assert isinstance(ClassificadorFactory.criar(), MockClassificador)
