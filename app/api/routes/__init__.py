from .pacientes import router as pacientes_router
from .triagens import router as triagens_router
from .medicos import router as medicos_router
from .consultas import router as consultas_router
from .fila import router as fila_router
from .agendamentos import router as agendamentos_router
from .auth import router as auth_router

all_routers = [
    auth_router,
    pacientes_router,
    triagens_router,
    medicos_router,
    consultas_router,
    fila_router,
    agendamentos_router,
]

__all__ = [
    "pacientes_router",
    "triagens_router",
    "medicos_router",
    "consultas_router",
    "fila_router",
    "agendamentos_router",
    "all_routers",
]
