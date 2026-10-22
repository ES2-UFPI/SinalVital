from app.database.models import Paciente, Triagem


def test_triagem_integrada_persiste_no_mesmo_banco(client, db_session):
    paciente = Paciente(nome="Paciente teste", email="triagem@example.com")
    db_session.add(paciente)
    db_session.commit()
    resposta = client.post(f"/pacientes/{paciente.id}/triagens", json={"relato": "dor no peito"})
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["classificacao"] == "laranja"
    assert dados["prioridade"] == 2
    registro = db_session.get(Triagem, dados["id"])
    assert registro.texto_sintomas == "dor no peito"
    assert registro.paciente_id == paciente.id


def test_triagem_paciente_ausente(client):
    resposta = client.post("/pacientes/999/triagens", json={"relato": "dor no peito"})
    assert resposta.status_code == 404


def test_triagem_estrategia_invalida(client, db_session):
    paciente = Paciente(nome="Paciente teste", email="estrategia@example.com")
    db_session.add(paciente)
    db_session.commit()
    resposta = client.post(f"/pacientes/{paciente.id}/triagens", json={
        "relato": "dor no peito", "estrategia": "inexistente",
    })
    assert resposta.status_code == 422
    assert db_session.query(Triagem).count() == 0
