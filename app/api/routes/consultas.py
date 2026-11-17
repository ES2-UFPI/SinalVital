from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.consulta import ConsultaCreate, ConsultaResponse
from app.database import get_db
from app.database.models import Consulta, EventoHistorico, ItemFila, Medico, Paciente, Triagem

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

    # Se existem itens na fila de atendimento no sistema, garante que o paciente
    # passou pela triagem/fila e foi alocado ao médico/especialidade correspondente.
    total_itens_fila = db.query(ItemFila).count()
    itens_paciente_fila = (
        db.query(ItemFila).filter(ItemFila.paciente_id == paciente.id).all()
    )
    triagens_paciente = (
        db.query(Triagem).filter(Triagem.paciente_id == paciente.id).all()
    )

    if total_itens_fila > 0 and not itens_paciente_fila and not triagens_paciente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"O paciente #{paciente.id} ({paciente.nome}) ainda não realizou triagem "
                f"e não está na fila de atendimento."
            ),
        )

    if itens_paciente_fila:
        alocado_ao_medico = any(
            item.medico_id == medico.id for item in itens_paciente_fila
        )
        if not alocado_ao_medico:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"O paciente #{paciente.id} ({paciente.nome}) não está alocado "
                    f"para {medico.nome} ({medico.especialidade})."
                ),
            )
        # Encerra o item ativo na fila de espera ao registrar a consulta,
        # liberando a vaga na capacidade simultânea do médico.
        itens_ativos_medico = [
            item
            for item in itens_paciente_fila
            if item.medico_id == medico.id
            and item.status in ("aguardando", "em_atendimento")
        ]
        if itens_ativos_medico:
            itens_ativos_medico[0].status = "atendido"
            itens_ativos_medico[0].atualizado_em = datetime.now(timezone.utc)
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
