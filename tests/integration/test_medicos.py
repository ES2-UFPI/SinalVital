import pytest
from sqlalchemy.exc import IntegrityError


def test_lista_vazia(client):
    resposta = client.get("/medicos")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_lista_medicos_por_nome(client, db_session):
    from app.database.models import Medico

    db_session.add_all([
        Medico(nome="Zélia", crm="000002-PI", especialidade="oftalmologia"),
        Medico(nome="Helena", crm="000001-PI", especialidade="cardiologia"),
    ])
    db_session.commit()
    resposta = client.get("/medicos")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert [m["nome"] for m in dados] == ["Helena", "Zélia"]
    assert dados[0] == {
        "id": db_session.query(Medico).filter_by(crm="000001-PI").one().id,
        "nome": "Helena", "crm": "000001-PI", "especialidade": "cardiologia",
    }


def test_crm_unico(db_session):
    from app.database.models import Medico

    db_session.add(Medico(nome="Helena", crm="000001-PI", especialidade="cardiologia"))
    db_session.commit()
    db_session.add(Medico(nome="Outra médica", crm="000001-PI", especialidade="clinica_geral"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(Medico).count() == 1


def test_seed_medicos_repetivel_preserva_edicoes(db_session):
    from app.database.models import Medico
    from app.seed import MEDICOS_DEMONSTRACAO, popular_medicos

    assert popular_medicos(db_session) == len(MEDICOS_DEMONSTRACAO)
    medico = db_session.query(Medico).filter_by(crm=MEDICOS_DEMONSTRACAO[0]["crm"]).one()
    medico.nome = "Nome atualizado"
    db_session.commit()
    assert popular_medicos(db_session) == 0
    db_session.refresh(medico)
    assert medico.nome == "Nome atualizado"
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
