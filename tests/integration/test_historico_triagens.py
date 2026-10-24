from datetime import datetime

from app.database.models import EventoHistorico, Paciente, Triagem


def test_historico_inclui_triagens_antigas_sem_duplicar_e_isola_paciente(client, db_session):
    paciente = Paciente(nome='Teste', email='historico-triagens@example.com')
    outro = Paciente(nome='Outro', email='outro-historico@example.com')
    db_session.add_all([paciente, outro])
    db_session.flush()
    instante = datetime(2026, 10, 1, 12)
    for paciente_id, texto, data in (
        (paciente.id, 'Tosse', instante),
        (paciente.id, 'Tosse', datetime(2026, 10, 2, 12)),
        (outro.id, 'Relato de outro paciente', instante),
    ):
        db_session.add(Triagem(paciente_id=paciente_id, relato=texto,
                               classificacao='verde', prioridade=4,
                               justificativa='Termo: tosse', criado_em=data))
    db_session.add_all([
        EventoHistorico(paciente_id=paciente.id, tipo_evento='triagem',
                        descricao='Tosse', urgencia='baixa', especialidade='clinica_geral',
                        criado_em=instante),
        EventoHistorico(paciente_id=paciente.id, tipo_evento='consulta',
                        descricao='Consulta de retorno', criado_em=datetime(2026, 10, 3, 12)),
    ])
    db_session.commit()
    url = f'/pacientes/{paciente.id}/historico'
    for _ in range(2):
        eventos = client.get(url).json()['eventos_historico']
        assert [e['descricao'] for e in eventos] == ['Tosse', 'Tosse', 'Consulta de retorno']
    assert len(client.get(url, params={'tipo_evento': 'triagem'}).json()['eventos_historico']) == 2
    consultas = client.get(url, params={'tipo_evento': 'consulta'}).json()['eventos_historico']
    assert [e['descricao'] for e in consultas] == ['Consulta de retorno']
    assert client.get(url, params={'tipo_evento': 'inexistente'}).json()['eventos_historico'] == []
    assert db_session.query(EventoHistorico).count() == 2
    assert db_session.query(Triagem).count() == 3
