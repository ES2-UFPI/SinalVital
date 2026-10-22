"""Inicialização da API e registro das rotas."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine
from app.api.routes.pacientes import router as pacientes_router
from app.api.routes.triagens import router as triagens_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SinalVital", lifespan=lifespan)
app.include_router(pacientes_router)
app.include_router(triagens_router)
