"""
Testes de integração para a fila de agendamentos e regras de médicos/disponibilidade.
Checklist coberto:
1. Divisão de médicos: médicos de urgência vs agendamento.
2. Lotação diária por data de atendimento e bloqueio quando atinge limite.
3. GET /agendamentos/disponibilidade com bloqueio de dias lotados.
4. POST /agendamentos com reaproveitamento do motivo como triagem (sem gastar mais tokens).
5. Recomendação de urgência caso motivo indique alta urgência.
6. GET /agendamentos retornando a fila agendada ordenada por prioridade fixa.
"""

from datetime import date, timedelta
import pytest
from app.database.models import Agendamento, Medico, Paciente, Triagem


def _proxima_data_dia_semana(dia_alvo: int) -> date:
    """Retorna a próxima data com o weekday desejado (0=segunda, 1=terça, 2=quarta, etc)."""
    hoje = date.today()
    dias_a_frente = (dia_alvo - hoje.weekday()) % 7
    if dias_a_frente == 0:
        dias_a_frente = 7
    return hoje + timedelta(days=dias_a_frente)


def _criar_paciente(db_session, nome="João Silva", email="joao@example.com", idade=30, condicao_cronica=None, gestante=False):
    paciente = Paciente(
        nome=nome,
        email=email,
        idade=idade,
        condicao_cronica=condicao_cronica,
        gestante=gestante,
    )
    db_session.add(paciente)
    db_session.commit()
    db_session.refresh(paciente)
    return paciente


def _criar_medico(
    db_session,
    nome="Dra. Mariana",
    especialidade="clinica_geral",
    tipo_atendimento="agendamento",
    dias_atendimento="segunda,quarta",
    limite_diario=2,
    ativo=True,
):
    medico = Medico(
        nome=nome,
        especialidade=especialidade,
        tipo_atendimento=tipo_atendimento,
        dias_atendimento=dias_atendimento,
        limite_diario=limite_diario,
        capacidade_simultanea=limite_diario,
        ativo=ativo,
    )
    db_session.add(medico)
    db_session.commit()
    db_session.refresh(medico)
    return medico


# ---------------------------------------------------------------------------
# 1. Divisão de Médicos (Urgência vs Agendamento)
# ---------------------------------------------------------------------------

def test_medico_apenas_urgencia_rejeita_agendamento(client, db_session):
    """Médico configurado apenas para 'urgencia' não pode receber agendamento."""
    paciente = _criar_paciente(db_session)
    medico_urgencia = _criar_medico(
        db_session,
        nome="Dr. Carlos Urgência",
        tipo_atendimento="urgencia",
        dias_atendimento="segunda,quarta",
        limite_diario=5,
    )
    segunda = _proxima_data_dia_semana(0)  # segunda-feira

    resposta = client.post(
        "/agendamentos",
        json={
            "paciente_id": paciente.id,
            "medico_id": medico_urgencia.id,
            "data_agendamento": segunda.isoformat(),
            "motivo": "Check-up de rotina",
        },
    )
    assert resposta.status_code == 400
    assert "agendamento" in resposta.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Dias de Atendimento e Lotação Diária
# ---------------------------------------------------------------------------

def test_medico_rejeita_agendamento_em_dia_que_nao_atende(client, db_session):
    """Se médico atende apenas segunda e quarta, agendamento na terça deve ser rejeitado."""
    paciente = _criar_paciente(db_session)
    medico = _criar_medico(
        db_session,
        dias_atendimento="segunda,quarta",
        limite_diario=3,
    )
    terca = _proxima_data_dia_semana(1)  # terça-feira

    resposta = client.post(
        "/agendamentos",
        json={
            "paciente_id": paciente.id,
            "medico_id": medico.id,
            "data_agendamento": terca.isoformat(),
            "motivo": "Consulta para renovar receita",
        },
    )
    assert resposta.status_code == 400
    assert "dia" in resposta.json()["detail"].lower()


def test_lotacao_diaria_bloqueia_dia_cheio(client, db_session):
    """
    Médico com limite diário = 2 na segunda-feira.
    2 agendamentos na segunda têm sucesso.
    3º agendamento na segunda é rejeitado com 400.
    Agendamento na quarta-feira (com vagas) tem sucesso.
    """
    medico = _criar_medico(
        db_session,
        dias_atendimento="segunda,quarta",
        limite_diario=2,
    )
    p1 = _criar_paciente(db_session, "P1", "p1@test.com")
    p2 = _criar_paciente(db_session, "P2", "p2@test.com")
    p3 = _criar_paciente(db_session, "P3", "p3@test.com")
    p4 = _criar_paciente(db_session, "P4", "p4@test.com")

    segunda = _proxima_data_dia_semana(0)
    quarta = _proxima_data_dia_semana(2)

    # 1º agendamento na segunda: OK
    r1 = client.post("/agendamentos", json={
        "paciente_id": p1.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Consulta de rotina",
    })
    assert r1.status_code == 201

    # 2º agendamento na segunda: OK (lotou o dia: 2/2)
    r2 = client.post("/agendamentos", json={
        "paciente_id": p2.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Consulta de rotina",
    })
    assert r2.status_code == 201

    # 3º agendamento na segunda: DEVE BLOQUEAR (400)
    r3 = client.post("/agendamentos", json={
        "paciente_id": p3.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Consulta de rotina",
    })
    assert r3.status_code == 400
    assert "limite" in r3.json()["detail"].lower() or "lotad" in r3.json()["detail"].lower()

    # 4º agendamento na quarta (dia com vagas abertas): OK
    r4 = client.post("/agendamentos", json={
        "paciente_id": p4.id, "medico_id": medico.id,
        "data_agendamento": quarta.isoformat(), "motivo": "Consulta de rotina",
    })
    assert r4.status_code == 201


def test_get_disponibilidade_mostra_dias_livres_e_lotados(client, db_session):
    """GET /agendamentos/disponibilidade retorna status de vagas por data."""
    medico = _criar_medico(
        db_session,
        dias_atendimento="segunda,quarta",
        limite_diario=1,
    )
    paciente = _criar_paciente(db_session)
    segunda = _proxima_data_dia_semana(0)

    # Antes do agendamento, segunda está disponível
    disp1 = client.get(f"/agendamentos/disponibilidade?medico_id={medico.id}&dias=14")
    assert disp1.status_code == 200
    dados_disp1 = disp1.json()
    item_segunda1 = next(d for d in dados_disp1 if d["data"] == segunda.isoformat())
    assert item_segunda1["disponivel"] is True
    assert item_segunda1["vagas_restantes"] == 1

    # Realiza agendamento na segunda
    client.post("/agendamentos", json={
        "paciente_id": paciente.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Rotina",
    })

    # Agora a segunda deve aparecer como não disponível (vagas_restantes = 0)
    disp2 = client.get(f"/agendamentos/disponibilidade?medico_id={medico.id}&dias=14")
    assert disp2.status_code == 200
    dados_disp2 = disp2.json()
    item_segunda2 = next(d for d in dados_disp2 if d["data"] == segunda.isoformat())
    assert item_segunda2["disponivel"] is False
    assert item_segunda2["vagas_restantes"] == 0


# ---------------------------------------------------------------------------
# 3. Reaproveitamento do Motivo como Triagem e Recomendação de Urgência
# ---------------------------------------------------------------------------

def test_agendamento_sem_triagem_previa_gera_triagem_e_recomenda_urgencia(client, db_session):
    """
    Quando o agendamento é feito sem triagem prévia, o motivo é analisado e salvo
    como Triagem no banco, informando se recomenda urgência.
    """
    paciente = _criar_paciente(db_session, "Maria", "maria@test.com")
    medico = _criar_medico(db_session, especialidade="cardiologia", dias_atendimento="segunda,quarta")
    segunda = _proxima_data_dia_semana(0)

    # Motivo de alta urgência cardíaca
    motivo_grave = "Dor forte no peito com suor frio e falta de ar"

    resposta = client.post("/agendamentos", json={
        "paciente_id": paciente.id,
        "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(),
        "motivo": motivo_grave,
    })
    assert resposta.status_code == 201
    dados = resposta.json()

    # Deve ter gerado uma triagem automaticamente
    assert dados["triagem_id"] is not None
    triagem_banco = db_session.get(Triagem, dados["triagem_id"])
    assert triagem_banco is not None
    assert triagem_banco.texto_sintomas == motivo_grave

    # Deve recomendar urgência para o paciente ir direto à fila de urgência se desejar
    assert dados["recomenda_urgencia"] is True
    assert dados["justificativa_urgencia"] is not None


def test_agendamento_com_triagem_previa_reaproveita_sem_reanalisar(client, db_session):
    """
    Se o paciente já possuir uma triagem_id, o agendamento reaproveita a mesma
    sem criar outra triagem e sem chamar a IA novamente.
    """
    paciente = _criar_paciente(db_session)
    medico = _criar_medico(db_session, especialidade="clinica_geral", dias_atendimento="segunda,quarta")
    segunda = _proxima_data_dia_semana(0)

    # Triagem prévia já existente
    triagem_previa = Triagem(
        paciente_id=paciente.id,
        texto_sintomas="Manchas avermelhadas na pele há uma semana",
        urgencia="baixa",
        especialidade="clinica_geral",
        justificativa="Quadro dermatológico estável",
    )
    db_session.add(triagem_previa)
    db_session.commit()
    db_session.refresh(triagem_previa)

    total_triagens_antes = db_session.query(Triagem).count()

    resposta = client.post("/agendamentos", json={
        "paciente_id": paciente.id,
        "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(),
        "motivo": "Acompanhamento de manchas na pele",
        "triagem_id": triagem_previa.id,
    })
    assert resposta.status_code == 201
    dados = resposta.json()

    assert dados["triagem_id"] == triagem_previa.id
    assert dados["recomenda_urgencia"] is False

    # Não deve ter criado nova triagem
    total_triagens_depois = db_session.query(Triagem).count()
    assert total_triagens_depois == total_triagens_antes


# ---------------------------------------------------------------------------
# 4. Fila Agendada Ordenada por Prioridade Fixa
# ---------------------------------------------------------------------------

def test_get_agendamentos_retorna_fila_ordenada_por_prioridade(client, db_session):
    """
    GET /agendamentos deve retornar os agendamentos ordenados por prioridade decrescente,
    considerando idade, gravidez e condições crônicas.
    """
    medico = _criar_medico(db_session, dias_atendimento="segunda,quarta", limite_diario=10)
    segunda = _proxima_data_dia_semana(0)

    # Paciente 1: Jovem saudável (menor prioridade)
    p_jovem = _criar_paciente(db_session, "Jovem", "jovem@test.com", idade=25)
    # Paciente 2: Gestante
    p_gestante = _criar_paciente(db_session, "Gestante", "gestante@test.com", idade=28, gestante=True)
    # Paciente 3: Superidosa com condição crônica (maior prioridade)
    p_idosa = _criar_paciente(db_session, "Idosa", "idosa@test.com", idade=85, condicao_cronica="Cardiopatia")

    # Inserção fora de ordem de prioridade
    client.post("/agendamentos", json={
        "paciente_id": p_jovem.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Consulta 1",
    })
    client.post("/agendamentos", json={
        "paciente_id": p_idosa.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Consulta 2",
    })
    client.post("/agendamentos", json={
        "paciente_id": p_gestante.id, "medico_id": medico.id,
        "data_agendamento": segunda.isoformat(), "motivo": "Consulta 3", "gestante": True,
    })

    resposta = client.get("/agendamentos")
    assert resposta.status_code == 200
    itens = resposta.json()
    assert len(itens) == 3

    # Ordenação esperada: Idosa (maior) > Gestante > Jovem
    assert itens[0]["paciente_id"] == p_idosa.id
    assert itens[1]["paciente_id"] == p_gestante.id
    assert itens[2]["paciente_id"] == p_jovem.id
    assert itens[0]["prioridade"] > itens[1]["prioridade"] > itens[2]["prioridade"]
