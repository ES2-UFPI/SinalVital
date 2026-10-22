from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.triagem import TriagemCreate, TriagemResponse
from app.database import get_db
from app.domain.triagem.factory import EstrategiaInvalidaError
from app.repositories.triagem_repository import TriagemRepository
from app.services.triagem_service import PacienteNaoEncontradoError, TriagemService

router = APIRouter(prefix="/pacientes", tags=["triagem"])


def get_triagem_service(db: Session = Depends(get_db)) -> TriagemService:
    return TriagemService(TriagemRepository(db))


@router.post(
    "/{paciente_id}/triagens",
    response_model=TriagemResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_triagem(
    paciente_id: int,
    payload: TriagemCreate,
    service: TriagemService = Depends(get_triagem_service),
):
    try:
        return service.realizar_triagem(paciente_id, payload.relato, payload.estrategia)
    except PacienteNaoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    except EstrategiaInvalidaError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
