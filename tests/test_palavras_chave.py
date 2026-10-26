import pytest

from app.domain.triagem.strategies.palavras_chave import PalavrasChaveStrategy


@pytest.mark.parametrize("relato, classificacao, prioridade", [
    ("Estou com dor no peito", "vermelho", 1),
  ("DOR NO PEITO!!!", "vermelho", 1),
  ("dór no péito", "vermelho", 1),
    ("Não consigo respirar direito", "laranja", 2),
    ("Meu pai desmaiou", "vermelho", 1),
    ("desmaiei agora", "vermelho", 1),
    ("Teve convulsao", "vermelho", 1),
    ("Estou com febre alta", "amarelo", 3),
    ("Tenho tosse", "verde", 4),
    ("Quero um check-up de rotina", "azul", 5),
])
def test_classificacao_ignora_caixa_e_acentos(relato, classificacao, prioridade):
    resultado = PalavrasChaveStrategy().classificar(relato)
    assert (resultado.classificacao, resultado.prioridade) == (classificacao, prioridade)


@pytest.mark.parametrize("relato, classificacao", [
    ("Sem dor no peito", "azul"),
    ("Não tenho falta de ar, só tosse", "verde"),
    ("Não sinto febre", "azul"),
])
def test_termos_negados_nao_contam(relato, classificacao):
    assert PalavrasChaveStrategy().classificar(relato).classificacao == classificacao


def test_nao_casa_parte_de_palavra():
    assert PalavrasChaveStrategy().classificar("Consultei o desmaiologista").classificacao == "azul"


def test_justificativa_mostra_termos_com_acento_sem_duplicar():
    r = PalavrasChaveStrategy().classificar("dor forte no peito e falta de ar")
    assert r.justificativa == "Termos identificados: dor forte no peito"
