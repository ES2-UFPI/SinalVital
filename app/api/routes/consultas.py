from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.consulta import ConsultaCreate, ConsultaResponse
from app.database import get_db
from app.database.models import (
    Agendamento,
    Consulta,
    EventoHistorico,
    ItemFila,
    Medico,
    Paciente,
    Triagem,
)

router = APIRouter(prefix="/consultas", tags=["consultas"])


@router.post(
    "",
    response_model=ConsultaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_consulta(dados: ConsultaCreate, db: Session = Depends(get_db)):
    paciente = db.get(Paciente, dados.paciente_id)
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente com id={dados.paciente_id} não encontrado.",
        )
    medico = db.get(Medico, dados.medico_id)
    if medico is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médico com id={dados.medico_id} não encontrado.",
        )

    # Verifica registros do paciente na Fila de Urgência (ItemFila) e na Fila de Consultas Agendadas (Agendamento)
    total_itens_fila = db.query(ItemFila).count()
    total_agendamentos = db.query(Agendamento).count()
    itens_paciente_fila = (
        db.query(ItemFila).filter(ItemFila.paciente_id == paciente.id).all()
    )
    agendamentos_paciente = (
        db.query(Agendamento).filter(Agendamento.paciente_id == paciente.id).all()
    )
    triagens_paciente = (
        db.query(Triagem).filter(Triagem.paciente_id == paciente.id).all()
    )

    if (
        (total_itens_fila > 0 or total_agendamentos > 0)
        and not itens_paciente_fila
        and not agendamentos_paciente
        and not triagens_paciente
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"O paciente #{paciente.id} ({paciente.nome}) ainda não realizou triagem "
                f"e não está na fila de atendimento."
            ),
        )

    # 1. Caso o paciente possua item na Fila de Urgência ou na Fila de Consultas Agendadas
    if itens_paciente_fila or agendamentos_paciente:
        itens_ativos_paciente = [
            item
            for item in itens_paciente_fila
            if item.status in ("aguardando", "em_atendimento")
        ]
        agendamentos_ativos_paciente = [
            ag
            for ag in agendamentos_paciente
            if ag.status in ("agendado", "em_atendimento")
        ]

        # Se há atendimentos ativos pendentes, valida a alocação sobre os ativos;
        # caso contrário, valida sobre o histórico de alocações do paciente.
        base_fila = (
            itens_ativos_paciente
            if (itens_ativos_paciente or agendamentos_ativos_paciente)
            else itens_paciente_fila
        )
        base_agendamentos = (
            agendamentos_ativos_paciente
            if (itens_ativos_paciente or agendamentos_ativos_paciente)
            else agendamentos_paciente
        )

        alocado_urgencia_medico = any(
            item.medico_id == medico.id for item in base_fila
        )
        alocado_agendamento_medico = any(
            ag.medico_id == medico.id for ag in base_agendamentos
        )

        if not alocado_urgencia_medico and not alocado_agendamento_medico:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"O paciente #{paciente.id} ({paciente.nome}) não está alocado "
                    f"para {medico.nome} ({medico.especialidade})."
                ),
            )

        # Se atendido por médico alocado na Fila de Urgência, encerra o item ativo e libera a vaga simultânea
        if alocado_urgencia_medico:
            itens_ativos_medico = [
                item
                for item in itens_ativos_paciente
                if item.medico_id == medico.id
            ]
            if itens_ativos_medico:
                itens_ativos_medico[0].status = "atendido"
                itens_ativos_medico[0].atualizado_em = datetime.now(timezone.utc)

        # Se atendido por médico alocado na Fila de Consultas Agendadas, encerra o agendamento ativo
        if alocado_agendamento_medico:
            agendamentos_ativos_medico = [
                ag
                for ag in agendamentos_ativos_paciente
                if ag.medico_id == medico.id
            ]
            if agendamentos_ativos_medico:
                agendamentos_ativos_medico[0].status = "atendido"
                agendamentos_ativos_medico[0].atualizado_em = datetime.now(timezone.utc)
    elif triagens_paciente:
        especialidade_compativel = any(
            (t.especialidade or "").lower() == (medico.especialidade or "").lower()
            for t in triagens_paciente
        )
        if not especialidade_compativel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"O paciente #{paciente.id} ({paciente.nome}) não foi direcionado "
                    f"para a especialidade {medico.especialidade} na triagem."
                ),
            )

    nova_consulta = Consulta(**dados.model_dump())
    evento_historico_consulta = EventoHistorico(
        paciente_id=paciente.id,
        especialidade=medico.especialidade,
        tipo_evento="consulta",
        descricao=(
            f"Médico(a): {medico.nome} | "
            f"Diagnóstico: {dados.diagnostico} | "
            f"Conduta: {dados.conduta}"
        ),
    )

    db.add(nova_consulta)
    db.add(evento_historico_consulta)
    db.commit()
    db.refresh(nova_consulta)
    return nova_consulta
