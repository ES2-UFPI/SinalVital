def test_consultar_dados_cadastrais_sem_carregar_historico(client, db_session):
    from app.database.models import Paciente
    paciente = Paciente(nome="Raimundo Nonato", email="raimundo.dados@example.com",
                        idade=65, condicao_cronica="Hipertensão")
    outro = Paciente(nome="Outra pessoa", email="outra.dados@example.com")
    db_session.add_all([paciente, outro])
    db_session.commit()
    resposta = client.get(f"/pacientes/{paciente.id}")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados['id'] == paciente.id
    assert dados['nome'] == 'Raimundo Nonato'
    assert dados['email'] == 'raimundo.dados@example.com'
    assert dados['idade'] == 65
    assert dados['condicao_cronica'] == 'Hipertensão'
    assert dados['criado_em']
    assert 'eventos_historico' not in dados


def test_consultar_dados_opcionais_nao_informados(client, db_session):
    from app.database.models import Paciente
    paciente = Paciente(nome="Ana", email="ana.dados@example.com")
    db_session.add(paciente)
    db_session.commit()
    dados = client.get(f"/pacientes/{paciente.id}").json()
    assert dados['idade'] is None
    assert dados['condicao_cronica'] is None


def test_consultar_paciente_inexistente(client):
    assert client.get('/pacientes/999999').status_code == 404


def test_tela_meus_dados_reutiliza_estilos_e_perfil(client):
    resposta = client.get('/pages/meus-dados.html')
    assert resposta.status_code == 200
    for trecho in ['data-page="dados"', '/assets/css/base.css', '/assets/js/auth.js',
                   '/assets/js/meus-dados.js', 'id="dados-paciente"', 'aria-live="polite"']:
        assert trecho in resposta.text
    assert '<form' not in resposta.text
