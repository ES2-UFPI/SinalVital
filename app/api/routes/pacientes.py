"""
Router de pacientes — SinalVital
=================================
Expõe endpoints relacionados a pacientes, incluindo a listagem cronológica
do histórico unificado de triagens e atendimentos.

Rota principal implementada aqui:
    GET /pacientes/{paciente_id}/historico
        Retorna os dados do paciente e todos os seus EventoHistorico
        ordenados cronologicamente (do mais antigo ao mais recente),
        com suporte a filtro opcional por tipo_evento.

Padrão arquitetural seguido:
    Apresentação (router) → Domínio (query no ORM) → Persistência (SQLAlchemy)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import EventoHistoricoResposta, HistoricoUnificadoResposta
from app.database import get_db
from app.database.models import EventoHistorico, Paciente

router = APIRouter(
    prefix="/pacientes",
    tags=["pacientes"],
)

# ---------------------------------------------------------------------------
# GET /pacientes/{paciente_id}/historico
# ---------------------------------------------------------------------------

@router.get(
    "/{paciente_id}/historico",
    response_model=HistoricoUnificadoResposta,
    summary="Histórico cronológico do paciente",
    description=(
        "Retorna os dados cadastrais do paciente e a lista de todos os seus "
        "eventos (triagens, atendimentos, etc.) ordenada do mais antigo ao "
        "mais recente. Use o parâmetro `tipo_evento` para filtrar por "
        "categoria específica."
    ),
)
def listar_historico_paciente(
    paciente_id: int,
    tipo_evento: Optional[str] = Query(
        default=None,
        description="Filtra por tipo de evento, ex: 'triagem', 'atendimento'.",
        examples=["triagem"],
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna o histórico cronológico (ASC) de triagens e atendimentos do
    paciente identificado por `paciente_id`.

    - **paciente_id**: identificador do paciente no banco.
    - **tipo_evento**: filtro opcional pelo campo `tipo_evento` do evento.

    Raises:
        404: quando o paciente não é encontrado.
    """
    # 1. Verifica existência do paciente (404 explícito)
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(
            status_code=404,
            detail=f"Paciente com id={paciente_id} não encontrado.",
        )

    # 2. Monta query base de eventos, sempre em ordem cronológica ASC
    query = (
        db.query(EventoHistorico)
        .filter(EventoHistorico.paciente_id == paciente_id)
        .order_by(EventoHistorico.criado_em.asc())
    )

    # 3. Aplica filtro opcional por tipo_evento
    if tipo_evento is not None:
        query = query.filter(EventoHistorico.tipo_evento == tipo_evento)

    eventos = query.all()

    # 4. Monta resposta usando os schemas Pydantic definidos em schemas
    return HistoricoUnificadoResposta(
        nome=paciente.nome,
        email=paciente.email,
        idade=paciente.idade,
        condicao_cronica=paciente.condicao_cronica,
        criado_em=paciente.criado_em,
        eventos_historico=[
            EventoHistoricoResposta.model_validate(e) for e in eventos
        ],
    )

