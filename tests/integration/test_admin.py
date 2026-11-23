from datetime import date
import pytest

PASSWORD = 'senha-ficticia-de-teste'
HEADERS = {'X-Admin-Password': PASSWORD}


@pytest.fixture(autouse=True)
def configurar_admin(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', PASSWORD)


@pytest.mark.parametrize('path,method', [('/admin/medicos','get'), ('/admin/medicos','post'),
                                       ('/admin/pacientes','get')])
@pytest.mark.parametrize('headers', [{}, {'X-Admin-Password':'incorreta'}])
def test_endpoints_admin_exigem_senha(client, path, method, headers):
    resposta = getattr(client, method)(path, headers=headers, **({'json':{}} if method=='post' else {}))
    assert resposta.status_code == 401


def test_admin_desabilitado_sem_configuracao(client, monkeypatch):
    monkeypatch.delenv('ADMIN_PASSWORD')
    assert client.get('/admin/medicos', headers=HEADERS).status_code == 503


def test_cadastrar_e_listar_medico_admin(client):
    dados = {'nome':'Dra. Exemplo','especialidade':'Clínica Geral',
             'tipo_atendimento':'agendamento','capacidade_simultanea':2,
             'dias_atendimento':'segunda,quarta','limite_diario':4,'ativo':True}
    resposta = client.post('/admin/medicos', json=dados, headers=HEADERS)
    assert resposta.status_code == 201
    medico = resposta.json()
    assert medico['id'] > 0
    assert medico['especialidade'] == 'clinica_geral'
    assert medico['dias_atendimento'] == 'segunda,quarta'
    assert medico['limite_diario'] == 4
    lista = client.get('/admin/medicos', headers=HEADERS)
    assert lista.status_code == 200
    assert lista.json() == [medico]
    assert lista.headers['cache-control'] == 'no-store'
    assert client.post('/admin/medicos', json=dados, headers=HEADERS).status_code == 409


@pytest.mark.parametrize('mudanca', [
    {'nome':'   '}, {'capacidade_simultanea':0}, {'tipo_atendimento':'invalido'},
    {'tipo_atendimento':'agendamento'},
    {'tipo_atendimento':'agendamento','dias_atendimento':'segunda','limite_diario':0},
    {'tipo_atendimento':'ambos','dias_atendimento':'dia-invalido','limite_diario':3},
])
def test_validacao_cadastro_medico(client, mudanca):
    dados = {'nome':'Exemplo','especialidade':'cardiologia','tipo_atendimento':'urgencia',
             'capacidade_simultanea':1, **mudanca}
    assert client.post('/admin/medicos', json=dados, headers=HEADERS).status_code == 422


def test_pacientes_sem_atendimento_sao_listados(client, db_session):
    from app.database.models import Paciente
    db_session.add(Paciente(nome='Ana', email='admin.ana@example.com'))
    db_session.commit()
    lista = client.get('/admin/pacientes', headers=HEADERS).json()
    assert len(lista)==1
    assert lista[0]['nome']=='Ana'
    assert lista[0]['atendimentos']==[]


def test_filtro_de_etapa_exibe_apenas_vinculos_correspondentes_sem_apagar_historico(client, db_session):
    from app.database.models import Paciente, Medico, Triagem, ItemFila, Agendamento, Consulta
    paciente = Paciente(nome='Raimundo', email='admin.raimundo@example.com')
    medico = Medico(nome='Helena', especialidade='cardiologia', ativo=True)
    outro = Paciente(nome='Outro', email='admin.outro@example.com')
    db_session.add_all([paciente, medico, outro]); db_session.commit()
    triagem = Triagem(paciente_id=paciente.id, texto_sintomas='Relato privado', urgencia='alta')
    db_session.add(triagem); db_session.commit()
    db_session.add_all([
        ItemFila(paciente_id=paciente.id, triagem_id=triagem.id, medico_id=medico.id, status='aguardando'),
        Agendamento(paciente_id=paciente.id, medico_id=medico.id, data_agendamento=date(2026,12,1),
                    motivo='Motivo privado', status='agendado'),
        Consulta(paciente_id=paciente.id, medico_id=medico.id, diagnostico='Diagnóstico privado',
                 conduta='Conduta privada', anamnese='Anamnese privada'),
    ]); db_session.commit()
    resposta = client.get('/admin/pacientes?nome=raimundo&etapa=agendado', headers=HEADERS)
    assert resposta.status_code == 200
    pacientes = resposta.json()
    assert len(pacientes)==1
    atendimentos=pacientes[0]['atendimentos']
    assert {a['tipo'] for a in atendimentos} == {'agendamento'}
    assert {a['etapa'] for a in atendimentos} == {'agendado'}
    for etapa in ['aguardando', 'atendido']:
        filtrados = client.get(f'/admin/pacientes?etapa={etapa}', headers=HEADERS).json()
        assert len(filtrados) == 1
        assert {a['etapa'] for a in filtrados[0]['atendimentos']} == {etapa}
    assert client.get('/admin/pacientes?etapa=cancelado', headers=HEADERS).json() == []
    historico = client.get('/admin/pacientes?nome=raimundo&etapa=todos', headers=HEADERS).json()
    assert {a['tipo'] for a in historico[0]['atendimentos']} == {'urgencia','agendamento','consulta'}
    assert all(a['medico_nome']=='Helena' for a in atendimentos)
    for texto in ['Diagnóstico privado','Conduta privada','Anamnese privada','Motivo privado','Relato privado']:
        assert texto not in resposta.text
    assert len(client.get('/admin/pacientes?etapa=sem_atendimento',headers=HEADERS).json()) == 1


def test_painel_separado_sem_link_publico(client):
    resposta=client.get('/pages/admin.html')
    assert resposta.status_code==200
    for trecho in ['/assets/css/base.css','/assets/js/admin.js','type="password"',
                   'role="tablist"','id="painel-pacientes"','id="painel-medicos"']:
        assert trecho in resposta.text
    assert '/pages/admin.html' not in client.get('/').text


def test_novo_medico_ativo_pode_entrar_no_painel_clinico(client):
    dados={'nome':'Profissional novo','especialidade':'cardiologia','capacidade_simultanea':1}
    medico=client.post('/admin/medicos',json=dados,headers=HEADERS).json()
    assert medico['tipo_atendimento']=='urgencia'
    assert medico['dias_atendimento'] is None
    assert client.post('/auth/login',json={
        'perfil':'medico','identificador':str(medico['id'])}).status_code==200


def test_triagem_sem_fila_e_exibida_sem_relato_clinico(client, db_session):
    from app.database.models import Paciente, Triagem
    paciente=Paciente(nome='Triagem pendente',email='triagem.admin@example.com')
    db_session.add(paciente); db_session.commit()
    db_session.add(Triagem(paciente_id=paciente.id,texto_sintomas='Relato reservado'))
    db_session.commit()
    resposta=client.get('/admin/pacientes?etapa=triagem',headers=HEADERS)
    assert resposta.status_code==200
    item=resposta.json()[0]['atendimentos'][0]
    assert item['tipo']=='triagem' and item['etapa']=='triagem'
    assert item['medico_nome'] is None
    assert 'Relato reservado' not in resposta.text
