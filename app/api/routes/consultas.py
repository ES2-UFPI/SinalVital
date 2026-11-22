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


def _encerrar_vinculo_ativo(registros_ativos: list, medico_id: int) -> None:
    """Marca como 'atendido' o primeiro vínculo ativo alocado ao médico informado."""
    for registro in registros_ativos:
        if registro.medico_id == medico_id:
            registro.status = "atendido"
            registro.atualizado_em = datetime.now(timezone.utc)
            break


def _validar_e_encerrar_alocacao_paciente(
    db: Session, paciente: Paciente, medico: Medico
) -> None:
    """
    Valida se o paciente passou por triagem/fila ou agendamento e se está alocado
    ao médico/especialidade informado, encerrando o vínculo ativo correspondente.
    """
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

        possui_vinculo_ativo = bool(
            itens_ativos_paciente or agendamentos_ativos_paciente
        )
        base_fila = (
            itens_ativos_paciente if possui_vinculo_ativo else itens_paciente_fila
        )
        base_agendamentos = (
            agendamentos_ativos_paciente
            if possui_vinculo_ativo
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

        if alocado_urgencia_medico:
            _encerrar_vinculo_ativo(itens_ativos_paciente, medico.id)

        if alocado_agendamento_medico:
            _encerrar_vinculo_ativo(agendamentos_ativos_paciente, medico.id)
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

    _validar_e_encerrar_alocacao_paciente(db, paciente, medico)

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
