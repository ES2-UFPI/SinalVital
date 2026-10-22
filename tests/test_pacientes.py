import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.database.models.models import Paciente
from app.database.models import Paciente
from app.seed import PACIENTES_DEMONSTRACAO, popular_pacientes


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'teste.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    # Sem iniciar o lifespan: somente o banco temporário é criado pela fixture.
    try:
        test_client = TestClient(app)
        yield test_client
        test_client.close()
    finally:
        app.dependency_overrides.clear()


def test_cadastro_persiste_e_retorna_identificador(client, db):
    resposta = client.post("/pacientes", json={
        "nome": " Raimundo Nonato ", "email": "raimundo@example.com",
        "idade": 65, "condicao_cronica": "Hipertensão",
    })
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["nome"] == "Raimundo Nonato"
    assert dados["idade"] == 65
    assert dados["condicao_cronica"] == "Hipertensão"
    assert dados["criado_em"]
    assert db.get(Paciente, dados["id"]).email == "raimundo@example.com"


def test_cadastro_minimo(client):
    resposta = client.post("/pacientes", json={"nome": "Ana", "email": "ana@example.com"})
    assert resposta.status_code == 201
    assert resposta.json()["idade"] is None
    assert resposta.json()["condicao_cronica"] is None


def test_email_duplicado(client, db):
    dados = {"nome": "Ana", "email": "ana@example.com"}
    assert client.post("/pacientes", json=dados).status_code == 201
    assert client.post("/pacientes", json=dados).status_code == 409
    assert db.query(Paciente).count() == 1


@pytest.mark.parametrize("alteracao", [
    {"nome": "   "}, {"nome": "a" * 121}, {"email": "invalido"},
    {"idade": -1}, {"condicao_cronica": "a" * 201}, {"email": None},
])
def test_dados_invalidos(client, db, alteracao):
    dados = {"nome": "Ana", "email": "ana@example.com", **alteracao}
    assert client.post("/pacientes", json=dados).status_code == 422
    assert db.query(Paciente).count() == 0


def test_seed_repetido_preserva_pacientes(db):
    existente = Paciente(nome="Nome preservado", email=PACIENTES_DEMONSTRACAO[0]["email"])
    db.add(existente)
    db.commit()
    assert popular_pacientes(db) == 1
    assert popular_pacientes(db) == 0
    assert db.query(Paciente).count() == 2
    db.refresh(existente)
    assert existente.nome == "Nome preservado"


def test_seed_banco_vazio(db):
    assert popular_pacientes(db) == 2
    assert {p.email for p in db.query(Paciente).all()} == {
        p["email"] for p in PACIENTES_DEMONSTRACAO
    }
