from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas.item_fila import ItemFilaCreate, ItemFilaResponse
from app.database import get_db
from app.database.models import ItemFila, Medico, Paciente, Triagem
from app.domain.queue.motor_priorizacao import (
    AGUARDANDO_VAGA_NA_ESPECIALIDADE,
    MotorPriorizacao,
    PESO_URGENCIA,
)

router = APIRouter(prefix="/fila", tags=["fila"])


@router.post(
    "",
    response_model=ItemFilaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inserir paciente triado na fila e alocar médico",
)
def inserir_na_fila(dados: ItemFilaCreate, db: Session = Depends(get_db)):
    """
    Insere o paciente triado na fila de espera e aloca o médico automaticamente
    utilizando MotorPriorizacao.escolher_medico().
    Calcula o score de prioridade conforme a urgência e o momento da triagem.
    """
    # 1. Verifica existência da triagem
    triagem = db.get(Triagem, dados.triagem_id)
    if triagem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triagem com id={dados.triagem_id} não encontrada.",
        )

    # 2. Determina e valida o paciente
    paciente_id = dados.paciente_id or triagem.paciente_id
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente com id={paciente_id} não encontrado.",
        )

    # 3. Calcula a pontuação (score) a partir da triagem [006-02]
    try:
        urgencia = triagem.urgencia.lower() if triagem.urgencia else "baixa"
        if urgencia not in PESO_URGENCIA:
            urgencia = "baixa"
        score = MotorPriorizacao.calcular_score(urgencia, triagem.criado_em)
    except Exception:
        score = dados.score if dados.score > 0.0 else 0.0

    # 4. Alocação automática do médico com escolher_medico() [008-02]
    medico_id = dados.medico_id
    if medico_id is None:
        especialidade = triagem.especialidade
        medicos = (
            db.query(Medico)
            .filter(Medico.ativo.is_(True), Medico.especialidade == especialidade)
            .all()
        )

        # Cargas atuais por médico na fila ativa
        cargas_raw = (
            db.query(ItemFila.medico_id, func.count(ItemFila.id))
            .filter(
                ItemFila.medico_id.isnot(None),
                ItemFila.status.in_(["aguardando", "em_atendimento"]),
            )
            .group_by(ItemFila.medico_id)
            .all()
        )
        carga_atual = {m_id: count for m_id, count in cargas_raw if m_id is not None}

        medico_escolhido = MotorPriorizacao.escolher_medico(
            especialidade=especialidade,
            medicos=medicos,
            carga_atual=carga_atual,
        )
        if medico_escolhido is not None:
            medico_id = medico_escolhido.id

    # 5. Cria e salva o ItemFila no banco
    novo_item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=medico_id,
        status=dados.status or "aguardando",
        score=score,
    )
    db.add(novo_item)
    db.commit()
    db.refresh(novo_item)

    return novo_item


@router.get(
    "",
    response_model=list[ItemFilaResponse],
    summary="Listar itens da fila ordenados por pontuação",
)
def listar_fila(
    status_filtro: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filtro opcional pelo status do item (ex: 'aguardando', 'em_atendimento')",
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna os itens da fila ordenados por pontuação decrescente (maior score primeiro).
    Apresenta motivo da triagem e médico alocado (ou 'Aguardando vaga na especialidade').
    """
    query = db.query(ItemFila)
    if status_filtro is not None:
        query = query.filter(ItemFila.status == status_filtro)

    itens = query.all()

    # Recalcula e atualiza o score de espera para itens em espera
    alterou_banco = False
    for item in itens:
        if item.triagem and item.triagem.urgencia:
            urg = item.triagem.urgencia.lower()
            if urg in PESO_URGENCIA:
                score_atual = MotorPriorizacao.calcular_score(urg, item.triagem.criado_em)
                if item.score != score_atual:
                    item.score = score_atual
                    alterou_banco = True

    # Ordena por score decrescente, e por horário de criação como desempate
    itens_ordenados = sorted(
        itens,
        key=lambda i: (-i.score, i.criado_em, i.id),
    )

    # Promove automaticamente pacientes que estavam 'Aguardando vaga na especialidade'
    # (medico_id is None e status == 'aguardando') caso uma vaga tenha sido liberada,
    # respeitando a ordem decrescente de prioridade (score).
    itens_sem_medico = [
        i
        for i in itens_ordenados
        if i.medico_id is None
        and i.status == "aguardando"
        and i.triagem is not None
        and i.triagem.especialidade
    ]
    if itens_sem_medico:
        cargas_raw = (
            db.query(ItemFila.medico_id, func.count(ItemFila.id))
            .filter(
                ItemFila.medico_id.isnot(None),
                ItemFila.status.in_(["aguardando", "em_atendimento"]),
            )
            .group_by(ItemFila.medico_id)
            .all()
        )
        carga_atual = {m_id: count for m_id, count in cargas_raw if m_id is not None}

        for item in itens_sem_medico:
            especialidade = item.triagem.especialidade
            medicos_esp = (
                db.query(Medico)
                .filter(Medico.ativo.is_(True), Medico.especialidade == especialidade)
                .all()
            )
            medico_escolhido = MotorPriorizacao.escolher_medico(
                especialidade=especialidade,
                medicos=medicos_esp,
                carga_atual=carga_atual,
            )
            if medico_escolhido is not None:
                item.medico_id = medico_escolhido.id
                item.medico = medico_escolhido
                carga_atual[medico_escolhido.id] = (
                    carga_atual.get(medico_escolhido.id, 0) + 1
                )
                alterou_banco = True

    if alterou_banco:
        db.commit()

    return itens_ordenados

