"""Verifica a entrega das páginas e o contrato usado pelo frontend."""


def test_paginas_e_assets_disponiveis(client):
    for path in ("/", "/pages/cadastro.html", "/pages/triagem.html", "/pages/historico.html"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'lang="pt-BR"' in response.text
        assert '/assets/css/base.css' in response.text
        assert '/assets/js/app.js' in response.text
    assert client.get('/assets/css/base.css').status_code == 200
    assert client.get('/assets/js/app.js').status_code == 200


def test_fluxo_api_utilizado_pelo_frontend(client):
    cadastro = client.post('/pacientes', json={'nome': 'Paciente Demo', 'email': 'demo@example.com'})
    assert cadastro.status_code == 201
    paciente_id = cadastro.json()['id']
    triagem = client.post(f'/pacientes/{paciente_id}/triagens', json={
        'relato': 'Estou com dor no peito', 'estrategia': 'palavras_chave',
    })
    assert triagem.status_code == 201
    assert triagem.json()['classificacao'] == 'laranja'
    historico = client.get(f'/pacientes/{paciente_id}/historico')
    assert historico.status_code == 200
    assert historico.json()['nome'] == 'Paciente Demo'
    eventos = historico.json()['eventos_historico']
    assert len(eventos) == 1
    assert eventos[0]['descricao'] == 'Estou com dor no peito'
    assert eventos[0]['urgencia'] == 'alta'
    assert eventos[0]['justificativa'] == triagem.json()['justificativa']
