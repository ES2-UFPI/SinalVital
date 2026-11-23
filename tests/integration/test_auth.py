import pytest


@pytest.fixture
def perfis(db_session):
    from app.database.models import Paciente, Medico
    paciente = Paciente(nome="Raimundo", email="raimundo@example.com")
    medico = Medico(nome="Helena", especialidade="cardiologia", ativo=True)
    inativo = Medico(nome="Inativo", especialidade="cardiologia", ativo=False)
    db_session.add_all([paciente, medico, inativo])
    db_session.commit()
    return paciente, medico, inativo


@pytest.mark.parametrize("por_email", [True, False])
def test_login_paciente(client, perfis, por_email):
    paciente, _, _ = perfis
    resposta = client.post("/auth/login", json={
        "perfil": "paciente", "identificador": paciente.email if por_email else str(paciente.id),
    })
    assert resposta.status_code == 200
    assert resposta.json() == {"perfil": "paciente", "id": paciente.id, "nome": paciente.nome}


def test_login_medico(client, perfis):
    _, medico, _ = perfis
    resposta = client.post("/auth/login", json={"perfil": "medico", "identificador": str(medico.id)})
    assert resposta.status_code == 200
    assert resposta.json() == {"perfil": "medico", "id": medico.id, "nome": medico.nome}


@pytest.mark.parametrize("perfil,identificador", [
    ("paciente", "999999"), ("paciente", "ausente@example.com"),
    ("medico", "999999"), ("medico", "nao-e-id"),
])
def test_login_inexistente(client, perfil, identificador):
    assert client.post("/auth/login", json={"perfil": perfil, "identificador": identificador}).status_code == 401


def test_medico_inativo_nao_entra(client, perfis):
    assert client.post("/auth/login", json={"perfil": "medico", "identificador": str(perfis[2].id)}).status_code == 401


@pytest.mark.parametrize("dados", [{}, {"perfil": "admin", "identificador": "1"},
    {"perfil": "paciente", "identificador": "   "}])
def test_login_dados_invalidos(client, dados):
    assert client.post("/auth/login", json=dados).status_code == 422


def test_tela_login_mantem_design_acessivel(client):
    resposta = client.get("/pages/login.html")
    assert resposta.status_code == 200
    for trecho in ["/assets/css/base.css", "/assets/js/auth.js", 'id="font-up"',
                   'id="contrast"', 'id="login-form"', 'aria-live="polite"',
                   'value="paciente"', 'value="medico"', '/pages/cadastro.html']:
        assert trecho in resposta.text
