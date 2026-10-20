from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Paciente
from .schemas import PacienteEntrada, PacienteResposta


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SinalVital", lifespan=lifespan)


@app.post("/pacientes", response_model=PacienteResposta, status_code=status.HTTP_201_CREATED)
def criar_paciente(dados: PacienteEntrada, db: Session = Depends(get_db)):
    if db.query(Paciente).filter(Paciente.email == str(dados.email)).first():
        raise HTTPException(status_code=409, detail="Já existe um paciente com esse e-mail.")

    paciente = Paciente(**dados.model_dump())
    db.add(paciente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Outra requisição pode ter cadastrado o mesmo e-mail após a consulta.
        if db.query(Paciente).filter(Paciente.email == str(dados.email)).first():
            raise HTTPException(status_code=409, detail="Já existe um paciente com esse e-mail.")
        raise
    db.refresh(paciente)
    return paciente
