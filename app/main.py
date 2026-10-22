"""
Entrypoint da aplicação SinalVital — FastAPI
Cria a instância `app`, registra os routers e garante que as tabelas
existam no banco de dados na inicialização.
"""
from pathlib import Path

"""Inicialização da API e registro das rotas."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database.database import Base, engine
from .routers import pacientes as pacientes_router
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database.database  import Base, engine, get_db
from .database.models.models import Paciente
from .api.schemas.schemas import PacienteEntrada, PacienteResposta
from app.database import Base, engine
from app.api.routes.pacientes import router as pacientes_router
from app.api.routes.triagens import router as triagens_router


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

FRONTEND_DIR = Path(__file__).resolve().parent().parent() / "fronted" # pega o caminho para o arqv atual, normaliza, pega seus 2 pais, e a pasta frontend
app.mount("/frontend",StaticFiles(directory=FRONTEND_DIR),"frontend")
app.include_router(pacientes_router)
app.include_router(triagens_router)
