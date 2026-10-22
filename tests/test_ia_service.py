import pytest

from app.ia_service import Classificador, ClassificadorFactory, MockClassificador


@pytest.fixture(autouse=True)
def ignorar_dotenv(monkeypatch):
    # O .env local do desenvolvedor não deve interferir nos cenários de configuração.
    monkeypatch.setattr("app.domain.triagem.strategies.classificador.load_dotenv", lambda: None)


def test_classificador_exige_implementacao():
    with pytest.raises(TypeError):
        Classificador()


def test_factory_padrao(monkeypatch):
    monkeypatch.delenv("MODO_IA", raising=False)
    assert isinstance(ClassificadorFactory.criar(), MockClassificador)


@pytest.mark.parametrize("modo", ["mock", "real", " MOCK ", " REAL "])
def test_factory_modos_suportados(monkeypatch, modo):
    monkeypatch.setenv("MODO_IA", modo)
    classificador = ClassificadorFactory.criar()
    assert isinstance(classificador, Classificador)
    assert isinstance(classificador, MockClassificador)
    assert classificador.classificar("dor no peito")["urgencia"] == "emergencia"


def test_factory_rele_configuracao(monkeypatch):
    monkeypatch.setenv("MODO_IA", "mock")
    ClassificadorFactory.criar()
    monkeypatch.setenv("MODO_IA", "invalido")
    with pytest.raises(ValueError, match="MODO_IA inválido"):
        ClassificadorFactory.criar()


@pytest.mark.parametrize("texto,urgencia,especialidade", [
    ("DOR NO PEITO e falta de ar", "emergencia", "cardiologia"),
    ("febre e dor forte", "alta", "clinica_geral"),
    ("mancha na pele", "baixa", "dermatologia"),
    ("mal-estar", "baixa", "clinica_geral"),
    ("febre e dor no peito", "emergencia", "cardiologia"),
])
def test_mock_contrato_e_regras_iniciais(texto, urgencia, especialidade):
    classificador = MockClassificador()
    resultado = classificador.classificar(texto)
    assert set(resultado) == {"urgencia", "especialidade", "justificativa"}
    assert resultado["urgencia"] == urgencia
    assert resultado["especialidade"] == especialidade
    assert resultado["justificativa"]
    assert resultado == classificador.classificar(texto)


def test_justificativa_identifica_termos():
    resultado = MockClassificador().classificar("dor no peito e falta de ar")
    assert "dor no peito, falta de ar" in resultado["justificativa"]


@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_mock_rejeita_relato_vazio(texto):
    with pytest.raises(ValueError, match="relato de sintomas"):
        MockClassificador().classificar(texto)
