"""Visão administrativa de vínculos; não expõe conteúdo do prontuário."""
from collections import defaultdict
from sqlalchemy.orm import Session
from app.database.models import Paciente, Medico, ItemFila, Agendamento, Consulta, Triagem


def listar_pacientes_atendimentos(db: Session, nome: str, etapa: str):
    query = db.query(Paciente)
    if nome:
        query = query.filter(Paciente.nome.icontains(nome, autoescape=True))
    pacientes = query.order_by(Paciente.nome, Paciente.id).all()
    if not pacientes:
        return []
    ids = [p.id for p in pacientes]
    medicos = {m.id: m.nome for m in db.query(Medico).all()}
    por_paciente = defaultdict(list)
    triagens_vinculadas = set()

    def adicionar(registro, tipo, status, data):
        medico_id = getattr(registro, 'medico_id', None)
        por_paciente[registro.paciente_id].append({
            'id': registro.id, 'tipo': tipo, 'etapa': status,
            'medico_id': medico_id, 'medico_nome': medicos.get(medico_id),
            'data': data.isoformat(),
        })

    for item in db.query(ItemFila).filter(ItemFila.paciente_id.in_(ids)).all():
        triagens_vinculadas.add(item.triagem_id)
        adicionar(item, 'urgencia', item.status, item.criado_em)
    for agendamento in db.query(Agendamento).filter(Agendamento.paciente_id.in_(ids)).all():
        if agendamento.triagem_id:
            triagens_vinculadas.add(agendamento.triagem_id)
        adicionar(agendamento, 'agendamento', agendamento.status, agendamento.data_agendamento)
    for consulta in db.query(Consulta).filter(Consulta.paciente_id.in_(ids)).all():
        adicionar(consulta, 'consulta', 'atendido', consulta.criado_em)
    for triagem in db.query(Triagem).filter(Triagem.paciente_id.in_(ids)).all():
        if triagem.id not in triagens_vinculadas:
            adicionar(triagem, 'triagem', 'triagem', triagem.criado_em)

    resultado = []
    for paciente in pacientes:
        itens = sorted(por_paciente[paciente.id], key=lambda item: (item['data'], item['tipo'], item['id']), reverse=True)
        if etapa == 'sem_atendimento' and itens:
            continue
        if etapa not in ('todos', 'sem_atendimento'):
            itens = [item for item in itens if item['etapa'] == etapa]
            if not itens:
                continue
        resultado.append({'id': paciente.id, 'nome': paciente.nome, 'atendimentos': itens})
    return resultado
