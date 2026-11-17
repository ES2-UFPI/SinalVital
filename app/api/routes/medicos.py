from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.medico import MedicoResposta
from app.database import get_db
from app.database.models import Medico

router = APIRouter(prefix="/medicos", tags=["medicos"])


@router.get("", response_model=list[MedicoResposta], summary="Listar médicos")
def listar_medicos(db: Session = Depends(get_db)):
    return db.query(Medico).order_by(Medico.nome.asc(), Medico.id.asc()).all()
