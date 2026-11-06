import pytest
from sqlalchemy.exc import IntegrityError


def test_lista_vazia(client):
    resposta = client.get("/medicos")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_lista_medicos_por_nome(client, db_session):
    from app.database.models import Medico

    db_session.add_all([
        Medico(nome="Zélia", capacidade_simultanea=2, ativo=False, especialidade="oftalmologia"),
        Medico(nome="Helena", capacidade_simultanea=3, ativo=True, especialidade="cardiologia"),
    ])
    db_session.commit()
    resposta = client.get("/medicos")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert [m["nome"] for m in dados] == ["Helena", "Zélia"]
    assert dados[1]["ativo"] is False
    assert dados[1]["capacidade_simultanea"] == 2
    assert dados[0] == {
        "id": db_session.query(Medico).filter_by(nome="Helena").one().id,
        "nome": "Helena", "especialidade": "cardiologia",
        "capacidade_simultanea": 3, "ativo": True,
    }


def test_valores_padrao_medico(db_session):
    from app.database.models import Medico

    medico = Medico(nome="Helena", especialidade="cardiologia")
    db_session.add(medico)
    db_session.commit()
    db_session.refresh(medico)
    assert medico.capacidade_simultanea == 1
    assert medico.ativo is True


@pytest.mark.parametrize("capacidade", [0, -1])
def test_capacidade_deve_ser_positiva(db_session, capacidade):
    from app.database.models import Medico

    db_session.add(Medico(nome="Helena", especialidade="cardiologia",
                         capacidade_simultanea=capacidade))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_seed_medicos_repetivel_preserva_edicoes(db_session):
    from app.database.models import Medico
    from app.seed import MEDICOS_DEMONSTRACAO, popular_medicos

    assert popular_medicos(db_session) == len(MEDICOS_DEMONSTRACAO)
    medico = db_session.query(Medico).filter_by(nome=MEDICOS_DEMONSTRACAO[0]["nome"],
                                               especialidade=MEDICOS_DEMONSTRACAO[0]["especialidade"]).one()
    medico.capacidade_simultanea = 5
    medico.ativo = False
    db_session.commit()
    assert popular_medicos(db_session) == 0
    db_session.refresh(medico)
    assert medico.capacidade_simultanea == 5
    assert medico.ativo is False
    assert db_session.query(Medico).count() == len(MEDICOS_DEMONSTRACAO)
    assert {m.especialidade for m in db_session.query(Medico)} >= {
        "cardiologia", "oftalmologia", "clinica_geral",
    }


def test_comando_seed_inclui_pacientes_e_medicos(db_session, monkeypatch, capsys):
    from app import seed
    from app.database.models import Medico, Paciente

    monkeypatch.setattr(seed, "engine", db_session.get_bind())
    # A sessão da fixture permanece aberta para verificar a persistência.
    from sqlalchemy.orm import sessionmaker
    monkeypatch.setattr(seed, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    seed.main()
    seed.main()
    assert db_session.query(Paciente).count() == len(seed.PACIENTES_DEMONSTRACAO)
    assert db_session.query(Medico).count() == len(seed.MEDICOS_DEMONSTRACAO)
    assert "médico(s)" in capsys.readouterr().out
