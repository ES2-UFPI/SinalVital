"""Verifica a entrega das páginas e o contrato usado pelo frontend."""

import re

from app.database.models import Medico

PAGINAS_COM_FEEDBACK = (
    "/pages/cadastro.html",
    "/pages/triagem.html",
    "/pages/medico.html",
    "/pages/historico.html",
    "/pages/fila.html",
)
TODAS_PAGINAS = ("/", *PAGINAS_COM_FEEDBACK)


def _extrair_scripts_inline(html: str) -> str:
    """Extrai o conteúdo das tags <script> inline (sem atributo src)."""
    blocos = re.findall(
        r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return "\n".join(blocos)


def _remover_comentarios_js(script: str) -> str:
    """Remove comentários JS de bloco e de linha inteira antes da inspeção."""
    sem_bloco = re.sub(r"/\*.*?\*/", "", script, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$", "", sem_bloco)


def _extrair_bloco_funcao_js(script: str, nome_funcao: str) -> str:
    """Extrai o corpo completo de uma função JavaScript por contagem de chaves."""
    match = re.search(rf"function\s+{re.escape(nome_funcao)}\s*\([^)]*\)\s*\{{", script)
    assert match is not None, f"Função JS {nome_funcao} não encontrada."
    inicio = match.start()
    abertura = match.end() - 1
    profundidade = 0
    for idx in range(abertura, len(script)):
        if script[idx] == "{":
            profundidade += 1
        elif script[idx] == "}":
            profundidade -= 1
            if profundidade == 0:
                return script[inicio : idx + 1]
    return script[inicio:]


def test_paginas_e_assets_disponiveis(client):
    for path in TODAS_PAGINAS:
        response = client.get(path)
        assert response.status_code == 200
        assert 'lang="pt-BR"' in response.text
        assert '/assets/css/base.css' in response.text
        assert '/assets/js/app.js' in response.text
    assert client.get('/assets/css/base.css').status_code == 200
    assert client.get('/assets/js/app.js').status_code == 200


def test_componentes_de_feedback_disponiveis(client):
    for path in PAGINAS_COM_FEEDBACK:
        response = client.get(path)
        assert response.status_code == 200
        html = response.text
        assert '/assets/css/feedback.css' in html
        assert '/assets/js/feedback.js' in html
        assert html.index('/assets/js/feedback.js') < html.index('/assets/js/app.js')
    assert client.get('/assets/css/feedback.css').status_code == 200
    js = client.get('/assets/js/feedback.js')
    assert js.status_code == 200
    assert 'const Feedback' in js.text


def test_fluxo_api_utilizado_pelo_frontend(client):
    cadastro = client.post('/pacientes', json={'nome': 'Paciente Demo', 'email': 'demo@example.com'})
    assert cadastro.status_code == 201
    paciente_id = cadastro.json()['id']
    triagem = client.post(f'/pacientes/{paciente_id}/triagens', json={
        'relato': 'Estou com dor no peito', 'estrategia': 'palavras_chave',
    })
    assert triagem.status_code == 201
    assert triagem.json()['classificacao'] == 'vermelho'
    historico = client.get(f'/pacientes/{paciente_id}/historico')
    assert historico.status_code == 200
    assert historico.json()['nome'] == 'Paciente Demo'
    eventos = historico.json()['eventos_historico']
    assert len(eventos) == 1
    assert eventos[0]['descricao'] == 'Estou com dor no peito'
    assert eventos[0]['urgencia'] == 'emergencia'
    assert eventos[0]['justificativa'] == triagem.json()['justificativa']


def test_fila_html_estrutura_e_controles_acessiveis(client):
    """GET /pages/fila.html deve expor estrutura semântica, aria-live e filtros acessíveis."""
    response = client.get('/pages/fila.html')
    assert response.status_code == 200
    assert 'text/html' in response.headers.get('content-type', '')

    html = response.text
    assert '<!doctype html>' in html.lower()
    assert 'lang="pt-BR"' in html
    assert 'data-page="fila"' in html

    assert 'class="skip"' in html
    assert 'href="#conteudo"' in html
    assert '<main id="conteudo" tabindex="-1">' in html
    assert 'id="font-down"' in html
    assert 'id="font-up"' in html
    assert 'id="contrast"' in html

    assert 'id="fila-lista"' in html
    assert 'id="busca-nome"' in html
    assert 'id="filtro-status"' in html
    assert 'id="btn-atualizar"' in html
    assert 'aria-live="polite"' in html
    assert 'value="aguardando"' in html
    assert 'value="em_atendimento"' in html
    assert 'value="atendido"' in html


def test_navegacao_para_fila_em_todas_as_paginas_e_card_inicial(client):
    """Todas as páginas devem possuir link de navegação para a fila e a home o card 05 · ACOMPANHAMENTO."""
    for pagina in TODAS_PAGINAS:
        response = client.get(pagina)
        assert response.status_code == 200
        html = response.text
        assert 'href="/pages/fila.html"' in html
        assert 'data-nav="fila"' in html
        assert re.search(
            r'<a\b(?=[^>]*href=["\']/pages/fila\.html["\'])(?=[^>]*data-nav=["\']fila["\'])',
            html,
        ) is not None

    index_html = client.get('/').text
    assert '05 · ACOMPANHAMENTO' in index_html
    assert re.search(
        r'<a\b[^>]*href=["\']/pages/fila\.html["\'][^>]*>'
        r'(?:(?!</a>).)*05\s*·\s*ACOMPANHAMENTO(?:(?!</a>).)*</a>',
        index_html,
        flags=re.DOTALL,
    ) is not None


def test_logica_posicao_fila_desconsidera_atendidos(client, db_session):
    """
    Garante que o script de /pages/fila.html calcula a posição a partir do status filtrado
    (desconsiderando atendidos e preservando a posição na busca) e valida via API que, após
    atendimento do mais prioritário, o segundo paciente vira o 1º aguardando na fila.
    """
    fila_html = client.get('/pages/fila.html')
    assert fila_html.status_code == 200

    script_limpo = _remover_comentarios_js(_extrair_scripts_inline(fila_html.text))
    assert script_limpo.strip(), 'Script inline de /pages/fila.html não encontrado.'
    assert re.search(r'todosOsItens\s*\.\s*indexOf\s*\(', script_limpo) is None

    bloco_render = _extrair_bloco_funcao_js(script_limpo, 'renderizarFila')
    assert 'criarCardFila(' in bloco_render
    assert 'statusFiltro' in bloco_render or 'filtroStatusEl' in bloco_render
    assert 'termo' in bloco_render or 'buscaEl' in bloco_render
    assert re.search(r'\bposic|\.(?:indexOf|findIndex)\(|\bMap\b', script_limpo, re.IGNORECASE) is not None
    assert re.search(r'filtrados\s*\.\s*forEach\s*\(\s*\(\s*\w+\s*,', bloco_render) is None

    dra_helena = Medico(
        nome='Dra. Helena',
        especialidade='cardiologia',
        capacidade_simultanea=2,
        ativo=True,
    )
    db_session.add(dra_helena)
    db_session.commit()
    db_session.refresh(dra_helena)

    resp_p1 = client.post(
        '/pacientes',
        json={'nome': 'Maria Prioritária', 'email': 'maria.fila@sinalvital.com', 'idade': 64},
    )
    resp_p2 = client.post(
        '/pacientes',
        json={'nome': 'João Segundo', 'email': 'joao.fila@sinalvital.com', 'idade': 38},
    )
    assert resp_p1.status_code == 201
    assert resp_p2.status_code == 201
    p1_id = resp_p1.json()['id']
    p2_id = resp_p2.json()['id']

    triagem_p1 = client.post(
        f'/pacientes/{p1_id}/triagens',
        json={'relato': 'Estou com dor no peito', 'estrategia': 'palavras_chave'},
    )
    triagem_p2 = client.post(
        f'/pacientes/{p2_id}/triagens',
        json={'relato': 'Acompanhamento de rotina do coração', 'estrategia': 'palavras_chave'},
    )
    assert triagem_p1.status_code == 201
    assert triagem_p2.status_code == 201
    assert triagem_p1.json()['urgencia'] == 'emergencia'
    assert triagem_p2.json()['urgencia'] == 'baixa'

    # Insere primeiro o de baixa urgência para comprovar ordenação por prioridade
    assert client.post('/fila', json={'triagem_id': triagem_p2.json()['id']}).status_code == 201
    assert client.post('/fila', json={'triagem_id': triagem_p1.json()['id']}).status_code == 201

    fila_inicial = client.get('/fila?status=aguardando')
    assert fila_inicial.status_code == 200
    assert [item['paciente_id'] for item in fila_inicial.json()] == [p1_id, p2_id]

    consulta = client.post(
        '/consultas',
        json={
            'paciente_id': p1_id,
            'medico_id': dra_helena.id,
            'diagnostico': 'Quadro torácico avaliado pela cardiologia',
            'conduta': 'Encaminhamento e monitorização contínua',
        },
    )
    assert consulta.status_code == 201

    fila_apos_atendimento = client.get('/fila?status=aguardando')
    assert fila_apos_atendimento.status_code == 200
    aguardando = fila_apos_atendimento.json()
    assert len(aguardando) == 1
    assert aguardando[0]['paciente_id'] == p2_id
    assert aguardando[0]['status'] == 'aguardando'

    fila_atendidos = client.get('/fila?status=atendido')
    assert fila_atendidos.status_code == 200
    atendidos = fila_atendidos.json()
    assert len(atendidos) == 1
    assert atendidos[0]['paciente_id'] == p1_id
    assert atendidos[0]['status'] == 'atendido'
    assert atendidos[0]['atualizado_em'] is not None


def test_fila_html_congela_tempo_e_exibe_horario_atendimento(client):
    """Card de paciente atendido deve congelar o tempo de espera e exibir quando foi atendido."""
    html = client.get('/pages/fila.html').text
    script_limpo = _remover_comentarios_js(_extrair_scripts_inline(html))
    bloco_card = _extrair_bloco_funcao_js(script_limpo, 'criarCardFila')

    assert 'status === "atendido"' in bloco_card
    assert 'Tempo de espera:' in bloco_card
    assert 'Atendido em:' in bloco_card
    assert 'formatarDuracaoEntre(item.criado_em, item.atualizado_em)' in bloco_card
    assert 'formatarDataHora(item.atualizado_em)' in bloco_card
    assert 'Aguardando há:' in bloco_card


def test_medico_html_exibe_espaco_do_medico_na_barra_lateral(client):
    """Painel médico deve identificar a barra lateral como ESPAÇO DO MÉDICO."""
    html = client.get('/pages/medico.html').text
    assert 'ESPAÇO DO MÉDICO' in html
    assert 'ESPAÇO DO PACIENTE' not in html


