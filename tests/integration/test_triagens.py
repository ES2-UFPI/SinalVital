from app.database.models import Paciente, Triagem


def test_triagem_integrada_persiste_no_mesmo_banco(client, db_session):
    paciente = Paciente(nome="Paciente teste", email="triagem@example.com")
    db_session.add(paciente)
    db_session.commit()

    resposta = client.post(
        f"/pacientes/{paciente.id}/triagens",
        json={"relato": "dor no peito"},
    )

    assert resposta.status_code == 201

    dados = resposta.json()
    assert dados["classificacao"] == "vermelho"
    assert dados["prioridade"] == 1
    assert dados["especialidade"] == "cardiologia"
    assert dados["urgencia"] == "emergencia"

    registro = db_session.get(Triagem, dados["id"])
    assert registro.texto_sintomas == "dor no peito"
    assert registro.paciente_id == paciente.id
    assert registro.especialidade == "cardiologia"
    assert registro.urgencia == "emergencia"


def test_triagem_paciente_ausente(client):
    resposta = client.post(
        "/pacientes/999/triagens",
        json={"relato": "dor no peito"},
    )

    assert resposta.status_code == 404


def test_triagem_estrategia_invalida(client, db_session):
    paciente = Paciente(nome="Paciente teste", email="estrategia@example.com")
    db_session.add(paciente)
    db_session.commit()

    resposta = client.post(
        f"/pacientes/{paciente.id}/triagens",
        json={
            "relato": "dor no peito",
            "estrategia": "inexistente",
        },
    )

    assert resposta.status_code == 422
    assert db_session.query(Triagem).count() == 0