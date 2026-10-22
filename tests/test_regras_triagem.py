import pytest

from app.triagem.regras import classificar_texto, normalizar


@pytest.mark.parametrize("texto, urgencia", [
    ("Estou com dor no peito e falta de ar", "emergencia"),
    ("Meu pai desmaiou e teve convulsão", "emergencia"),
    ("Estou com febre alta desde ontem", "alta"),
    ("Tenho vômito e tontura", "alta"),
    ("Tosse seca e dor de garganta", "media"),
    ("Coceira nos olhos e olho seco", "media"),
    ("Quero marcar um check-up de rotina", "baixa"),
    ("", "baixa"),
    ("   ", "baixa"),
])
def test_cada_nivel_de_urgencia(texto, urgencia):
    assert classificar_texto(texto).urgencia == urgencia


def test_nivel_mais_alto_vence():
    r = classificar_texto("Tenho tosse, febre e dor no peito")
    assert r.urgencia == "emergencia"
    assert r.termos_urgencia == ("dor no peito",)  # só termos do nível vencedor


def test_persona_raimundo_cardiologia():
    r = classificar_texto("Sou cardiopata, estou com dor no peito e falta de ar")
    assert (r.urgencia, r.especialidade) == ("emergencia", "cardiologia")
    assert r.justificativa.startswith(
        "Classificado como emergência por mencionar: dor no peito, falta de ar")
    assert "cardiologia" in r.justificativa


def test_persona_juscelio_oftalmologia():
    r = classificar_texto("Meus olhos estão secos e coço bastante, com coceira nos olhos")
    assert r.especialidade == "oftalmologia"
    assert r.urgencia == "media"


def test_clinica_geral_por_padrao():
    r = classificar_texto("Estou com tosse")
    assert r.especialidade == "clinica_geral"
    assert "clínica geral" in r.justificativa


def test_justificativa_sem_termos_de_urgencia():
    r = classificar_texto("Gostaria de uma consulta")
    assert r.urgencia == "baixa"
    assert r.justificativa.startswith("Nenhum termo de urgência identificado")


@pytest.mark.parametrize("texto", [
    "DOR NO PEITO!!!", "dór no péito", "  dor   no\npeito  ",
])
def test_ignora_caixa_acento_e_espacos(texto):
    assert classificar_texto(texto).urgencia == "emergencia"


def test_normalizar():
    assert normalizar("  Dór,  NO\tPéito! ") == "dor no peito"


@pytest.mark.parametrize("texto, urgencia", [
    ("Não tenho falta de ar", "baixa"),
    ("Sem dor no peito, só tosse", "media"),
    ("Não sinto febre, mas estou com falta de ar", "emergencia"),
    ("Não consigo respirar direito", "emergencia"),
])
def test_negacao(texto, urgencia):
    assert classificar_texto(texto).urgencia == urgencia


def test_termo_mais_longo_nao_duplica():
    r = classificar_texto("dor forte no peito")
    assert r.urgencia == "emergencia"
    assert r.termos_urgencia == ("dor forte no peito",)


def test_nao_casa_parte_de_palavra():
    assert classificar_texto("Vomitei de rir").urgencia == "baixa"
    assert classificar_texto("Consultei o desmaiologista").urgencia == "baixa"


def test_texto_nulo_nao_quebra():
    assert classificar_texto(None).urgencia == "baixa"


def test_justificativa_exibe_termos_com_acento():
    r = classificar_texto("Estou com vomito e visao turva")
    assert "vômito, visão turva" in r.justificativa
