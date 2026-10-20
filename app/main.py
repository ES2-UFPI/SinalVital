"""
Entrypoint da aplicação SinalVital — FastAPI
============================================
Cria a instância `app`, registra os routers e garante que as tabelas
existam no banco de dados na inicialização.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routers import pacientes as pacientes_router


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
