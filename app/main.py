"""
Entrypoint da aplicação SinalVital — FastAPI
Cria a instância `app`, registra os routers e garante que as tabelas
existam no banco de dados na inicialização.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routers import pacientes as pacientes_router
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Paciente
from .schemas import PacienteEntrada, PacienteResposta


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas no banco caso ainda não existam (útil em dev/SQLite)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="SinalVital",
    description=(
        "Plataforma de telemedicina com triagem por IA, fila inteligente "
        "e monitoramento contínuo."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Registro de routers
# ---------------------------------------------------------------------------
app.include_router(pacientes_router.router)
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
