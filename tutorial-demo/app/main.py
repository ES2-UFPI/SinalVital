import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models
from .ia_service import classificar_sintomas, MODO_IA

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SinalVital — Projeto de demonstração dos tutoriais")


class SaudacaoEntrada(BaseModel):
    nome: str


class SaudacaoResposta(BaseModel):
    mensagem: str


class PacienteEntrada(BaseModel):
    nome: str
    email: str


class PacienteResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: str


class ClassificacaoEntrada(BaseModel):
    texto_sintomas: str


# --- Tutorial 2: exemplo básico ---
@app.post("/saudacao", response_model=SaudacaoResposta)
def saudacao(dados: SaudacaoEntrada):
    return {"mensagem": f"Olá, {dados.nome}! Bem-vindo ao SinalVital."}


# --- Tutorial 3: persistência ---
@app.post("/pacientes", response_model=PacienteResposta)
def criar_paciente(dados: PacienteEntrada, db: Session = Depends(get_db)):
    if db.query(models.Paciente).filter(models.Paciente.email == dados.email).first():
        raise HTTPException(status_code=400, detail="Já existe um paciente com esse e-mail.")
    paciente = models.Paciente(nome=dados.nome, email=dados.email)
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente


@app.get("/pacientes", response_model=list[PacienteResposta])
def listar_pacientes(db: Session = Depends(get_db)):
    return db.query(models.Paciente).all()


# --- Tutorial 5: tecnologia específica (IA) ---
@app.post("/classificar")
def classificar(dados: ClassificacaoEntrada):
    try:
        resultado = classificar_sintomas(dados.texto_sintomas)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao classificar: {e}")
    return {"modo_ia": MODO_IA, **resultado}


@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse(url="/painel/")


# --- Tutorial 4: painel web (cliente) ---
app.mount(
    "/painel",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True),
    name="painel",
)
