"""Inicialização da API e registro das rotas."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.api.routes import all_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SinalVital", lifespan=lifespan)
for router in all_routers:
    app.include_router(router)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")
app.mount("/pages", StaticFiles(directory=FRONTEND / "pages", html=True), name="pages")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONTEND / "index.html")
