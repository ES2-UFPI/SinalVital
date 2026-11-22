from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.auth import LoginEntrada, PerfilResposta
from app.database import get_db
from app.database.models import Paciente, Medico

router = APIRouter(prefix="/auth", tags=["identificacao"])


@router.post("/login", response_model=PerfilResposta,
             summary="Identificar perfil de demonstração (sem senha)")
def login(dados: LoginEntrada, db: Session = Depends(get_db)):
    identificador = dados.identificador
    pessoa = None
    if dados.perfil == "paciente" and "@" in identificador:
        pessoa = db.query(Paciente).filter(Paciente.email == identificador).first()
    elif identificador.isascii() and identificador.isdigit() and 0 < len(identificador) <= 18:
        modelo = Paciente if dados.perfil == "paciente" else Medico
        pessoa = db.get(modelo, int(identificador))
    if pessoa is None or (dados.perfil == "medico" and not pessoa.ativo):
        raise HTTPException(status_code=401, detail="Perfil não encontrado ou indisponível. Confira os dados.")
    return PerfilResposta(perfil=dados.perfil, id=pessoa.id, nome=pessoa.nome)
