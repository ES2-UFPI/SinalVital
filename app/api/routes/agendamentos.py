from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.agendamento import (
    AgendamentoCreate,
    AgendamentoResponse,
    DisponibilidadeDiaResponse,
    MedicoAgendamentoResponse,
)
from app.database import get_db
from app.database.models import Agendamento, Medico, Paciente, Triagem
from app.domain.agendamento.priorizacao import calcular_prioridade_agendamento
from app.domain.triagem.strategies.classificador import ClassificadorFactory

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])


@router.get(
    "/medicos",
    response_model=list[MedicoAgendamentoResponse],
    summary="Listar médicos disponíveis para agendamento",
)
def listar_medicos_agendamento(
    especialidade: Optional[str] = Query(None, description="Filtrar por especialidade"),
    db: Session = Depends(get_db),
):
    query = db.query(Medico).filter(
        Medico.ativo.is_(True),
        Medico.tipo_atendimento.in_(["agendamento", "ambos"]),
    )
    if especialidade:
        query = query.filter(Medico.especialidade == especialidade.lower().strip())

    return query.order_by(Medico.nome.asc()).all()

MAPA_DIAS_SEMANA_NOMES = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

MAPA_URGENCIA_CLASSIFICACAO = {
    "emergencia": ("vermelho", 1),
    "alta": ("laranja", 2),
    "media": ("amarelo", 3),
    "baixa": ("verde", 4),
}


@router.get(
    "/disponibilidade",
    response_model=list[DisponibilidadeDiaResponse],
    summary="Verificar disponibilidade de dias e vagas de um médico",
)
def verificar_disponibilidade(
    medico_id: int = Query(..., description="ID do médico"),
    data_inicio: Optional[date] = Query(None, description="Data de início da consulta de disponibilidade"),
    dias: int = Query(14, ge=1, le=60, description="Quantidade de dias futuros a verificar"),
    data: Optional[date] = Query(None, description="Consultar apenas uma data específica"),
    db: Session = Depends(get_db),
):
    medico = db.get(Medico, medico_id)
    if medico is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médico com id={medico_id} não encontrado.",
        )

    if not medico.atende_agendamento():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O médico {medico.nome} atende apenas urgência e não realiza agendamentos.",
        )

    vagas_totais = medico.limite_diario if medico.limite_diario and medico.limite_diario > 0 else 1

    if data is not None:
        datas_a_verificar = [data]
    else:
        inicio = data_inicio or date.today()
        datas_a_verificar = [inicio + timedelta(days=i) for i in range(dias)]

    resultado: list[DisponibilidadeDiaResponse] = []

    for d in datas_a_verificar:
        if not medico.atende_em_dia(d):
            continue

        ocupadas = (
            db.query(Agendamento)
            .filter(
                Agendamento.medico_id == medico.id,
                Agendamento.data_agendamento == d,
                Agendamento.status != "cancelado",
            )
            .count()
        )
        restantes = max(0, vagas_totais - ocupadas)
        disponivel = restantes > 0

        resultado.append(
            DisponibilidadeDiaResponse(
                data=d,
                dia_semana=MAPA_DIAS_SEMANA_NOMES.get(d.weekday(), "dia"),
                vagas_totais=vagas_totais,
                vagas_ocupadas=ocupadas,
                vagas_restantes=restantes,
                disponivel=disponivel,
            )
        )

    return resultado


@router.post(
    "",
    response_model=AgendamentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar consulta agendada com triagem e cálculo de prioridade fixa",
)
def criar_agendamento(dados: AgendamentoCreate, db: Session = Depends(get_db)):
    # 1. Valida paciente
    paciente = db.get(Paciente, dados.paciente_id)
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente com id={dados.paciente_id} não encontrado.",
        )

    # 2. Valida médico
    medico = db.get(Medico, dados.medico_id)
    if medico is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médico com id={dados.medico_id} não encontrado.",
        )

    # 3. Diferenciação: atende agendamento?
    if not medico.atende_agendamento():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O médico {medico.nome} atende apenas urgência e não realiza agendamentos.",
        )

    # 4. Atende no dia da semana?
    if not medico.atende_em_dia(dados.data_agendamento):
        dia_nome = MAPA_DIAS_SEMANA_NOMES.get(dados.data_agendamento.weekday(), "este dia")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O médico {medico.nome} não atende em {dia_nome}. Dias de atendimento: {medico.dias_atendimento}.",
        )

    # 5. Lotação diária
    limite = medico.limite_diario if medico.limite_diario and medico.limite_diario > 0 else 1
    ocupadas_no_dia = (
        db.query(Agendamento)
        .filter(
            Agendamento.medico_id == medico.id,
            Agendamento.data_agendamento == dados.data_agendamento,
            Agendamento.status != "cancelado",
        )
        .count()
    )
    if ocupadas_no_dia >= limite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite diário de pacientes do médico {medico.nome} atingido para {dados.data_agendamento}. Escolha outro dia disponível.",
        )

    # Atualiza gestante no paciente se fornecido
    is_gestante = dados.gestante if dados.gestante is not None else bool(paciente.gestante)
    if dados.gestante is not None and paciente.gestante != dados.gestante:
        paciente.gestante = dados.gestante

    # 6. Análise de motivo com IA e reaproveitamento como Triagem
    triagem_id = dados.triagem_id
    urgencia = "baixa"
    justificativa = None

    if triagem_id is not None:
        triagem_existente = db.get(Triagem, triagem_id)
        if triagem_existente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Triagem com id={triagem_id} não encontrada.",
            )
        urgencia = triagem_existente.urgencia or "baixa"
        justificativa = triagem_existente.justificativa
    else:
        # Analisa o motivo com a IA sem criar duplicidade de triagem
        classificador = ClassificadorFactory.criar()
        resultado_ia = classificador.classificar(dados.motivo)
        urgencia = resultado_ia.get("urgencia", "baixa")
        justificativa = resultado_ia.get("justificativa", "")
        especialidade_ia = resultado_ia.get("especialidade") or medico.especialidade or "clinica_geral"

        classificacao_cor, prioridade_num = MAPA_URGENCIA_CLASSIFICACAO.get(
            urgencia, ("verde", 4)
        )

        nova_triagem = Triagem(
            paciente_id=paciente.id,
            texto_sintomas=dados.motivo,
            urgencia=urgencia,
            especialidade=especialidade_ia,
            justificativa=justificativa,
            classificacao=classificacao_cor,
            prioridade=prioridade_num,
            estrategia="ia_agendamento",
        )
        db.add(nova_triagem)
        db.flush()
        triagem_id = nova_triagem.id

    # Recomendação de urgência caso motivo indique alta urgência
    recomenda_urgencia = urgencia in ("emergencia", "alta")
    justificativa_urgencia = justificativa if recomenda_urgencia else None

    # 7. Cálculo de prioridade fixa
    prioridade_fixa = calcular_prioridade_agendamento(
        idade=paciente.idade,
        gestante=is_gestante,
        condicao_cronica=paciente.condicao_cronica,
        urgencia=urgencia,
    )

    # 8. Persiste Agendamento
    agendamento = Agendamento(
        paciente_id=paciente.id,
        medico_id=medico.id,
        triagem_id=triagem_id,
        data_agendamento=dados.data_agendamento,
        motivo=dados.motivo,
        prioridade=prioridade_fixa,
        status="agendado",
        recomenda_urgencia=recomenda_urgencia,
        justificativa_urgencia=justificativa_urgencia,
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)

    return agendamento


@router.get(
    "",
    response_model=list[AgendamentoResponse],
    summary="Listar fila de agendamentos ordenada por prioridade",
)
def listar_agendamentos(
    medico_id: Optional[int] = Query(None, description="Filtrar por médico"),
    data: Optional[date] = Query(None, description="Filtrar por data específica"),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    db: Session = Depends(get_db),
):
    query = db.query(Agendamento)

    if medico_id is not None:
        query = query.filter(Agendamento.medico_id == medico_id)
    if data is not None:
        query = query.filter(Agendamento.data_agendamento == data)
    if status_filtro is not None:
        query = query.filter(Agendamento.status == status_filtro)

    # Ordenação por prioridade fixa decrescente (maior score primeiro)
    agendamentos = query.order_by(
        Agendamento.prioridade.desc(),
        Agendamento.data_agendamento.asc(),
        Agendamento.criado_em.asc(),
    ).all()

    return agendamentos
