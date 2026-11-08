from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.consulta import ConsultaCreate, ConsultaResponse
from app.database import get_db
from app.database.models import Consulta, EventoHistorico, Medico, Paciente

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

    nova_consulta = Consulta(**dados.model_dump())
    evento_historico_consulta = EventoHistorico(
        paciente_id=paciente.id,
        especialidade=medico.especialidade,
        tipo_evento="consulta",
        descricao=f"Diagnóstico: {dados.diagnostico} | Conduta: {dados.conduta}",
    )

    db.add(nova_consulta)
    db.add(evento_historico_consulta)
    db.commit()
    db.refresh(nova_consulta)
    return nova_consulta
