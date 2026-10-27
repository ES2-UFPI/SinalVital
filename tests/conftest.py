"""
conftest.py — fixtures compartilhadas entre todos os testes do SinalVital
=========================================================================
Estratégia de isolamento:
  - Um SQLite em memória é criado por módulo de teste (escopo "session").
  - As tabelas são criadas/destruídas por função de teste (escopo "function").
  - O override de dependência substitui get_db da app pela sessão de teste,
    garantindo que toda requisição HTTP use o mesmo banco em memória.
  - O TestClient é criado dentro do contexto do lifespan (with TestClient(app))
    para disparar o evento de startup corretamente.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# Engine e SessionFactory de teste
# ---------------------------------------------------------------------------
# StaticPool força o SQLite a reutilizar a MESMA conexão em memória para
# todos os acessos — sem isso, cada nova conexão abre um banco diferente e
# as tabelas criadas em uma conexão não ficam visíveis na outra.
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_test
)


# ---------------------------------------------------------------------------
# Fixture: tabelas
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_tables(monkeypatch):
    """Cria as tabelas antes de cada teste e as destrói ao final."""
    monkeypatch.setattr("app.main.engine", engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


# ---------------------------------------------------------------------------
# Fixture: sessão de banco disponível para os testes inserirem dados
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(setup_tables):
    """
    Fornece uma sessão SQLAlchemy conectada ao banco de teste.
    Fechada automaticamente ao final do teste.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixture: TestClient com override de dependência
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(setup_tables):
    """
    TestClient do FastAPI com get_db substituído pelo banco em memória.
    Depende de setup_tables para garantir que as tabelas existam antes
    do primeiro request.
    """
    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    # Limpa o override ao final para não vazar entre módulos de teste
    app.dependency_overrides.clear()
