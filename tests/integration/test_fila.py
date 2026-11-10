"""
Testes de integração para os endpoints da fila: POST /fila e GET /fila (Issue #44)
==================================================================================
Checklist coberto:
    1. POST /fila cria ItemFila a partir de uma triagem e aloca o médico com escolher_medico().
    2. GET /fila retorna os itens ordenados por pontuação, com motivo e médico alocado.
    3. Sem vaga, o item aparece como "Aguardando vaga na especialidade".
    4. Testes de integração cobrindo fluxos felizes, distribuição de carga, ordenação e erros.
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.database.models import ItemFila, Medico, Paciente, Triagem
from app.domain.queue.motor_priorizacao import AGUARDANDO_VAGA_NA_ESPECIALIDADE


# ---------------------------------------------------------------------------
# Helpers para criação de dados nos testes
# ---------------------------------------------------------------------------

def _criar_paciente(db_session, nome="Carlos Eduardo", email="carlos@example.com"):
    paciente = Paciente(nome=nome, email=email, idade=45)
    db_session.add(paciente)
    db_session.commit()
    db_session.refresh(paciente)
    return paciente


def _criar_triagem(
    db_session,
    paciente_id,
    urgencia="alta",
    especialidade="cardiologia",
    texto_sintomas="Dor no peito com irradiação para o braço",
    justificativa="Quadro sugestivo de síndrome coronariana",
    delta_minutos=0,
):
    criado_em = datetime.now(timezone.utc) - timedelta(minutes=delta_minutos)
    triagem = Triagem(
        paciente_id=paciente_id,
        texto_sintomas=texto_sintomas,
        urgencia=urgencia,
        especialidade=especialidade,
        justificativa=justificativa,
        criado_em=criado_em,
    )
    db_session.add(triagem)
    db_session.commit()
    db_session.refresh(triagem)
    return triagem


def _criar_medico(
    db_session,
    nome="Dra. Helena",
    especialidade="cardiologia",
    capacidade_simultanea=2,
    ativo=True,
):
    medico = Medico(
        nome=nome,
        especialidade=especialidade,
        capacidade_simultanea=capacidade_simultanea,
        ativo=ativo,
    )
    db_session.add(medico)
    db_session.commit()
    db_session.refresh(medico)
    return medico


# ---------------------------------------------------------------------------
# Testes do POST /fila
# ---------------------------------------------------------------------------

def test_post_fila_sucesso_aloca_medico(client, db_session):
    """POST /fila cria o ItemFila e aloca médico da especialidade disponível."""
    paciente = _criar_paciente(db_session)
    triagem = _criar_triagem(db_session, paciente.id, urgencia="alta", especialidade="cardiologia")
    medico = _criar_medico(db_session, nome="Dra. Helena", especialidade="cardiologia", capacidade_simultanea=2)

    resposta = client.post("/fila", json={"triagem_id": triagem.id})
    assert resposta.status_code == 201

    dados = resposta.json()
    assert dados["triagem_id"] == triagem.id
    assert dados["paciente_id"] == paciente.id
    assert dados["medico_id"] == medico.id
    assert dados["medico_alocado"] == "Dra. Helena"
    assert dados["status"] == "aguardando"
    assert dados["score"] >= 55.0  # urgência alta inicia em 55
    assert dados["motivo"] == triagem.justificativa
    assert dados["urgencia"] == "alta"
    assert dados["especialidade"] == "cardiologia"

    # Confirma que foi persistido no banco de dados
    item_banco = db_session.get(ItemFila, dados["id"])
    assert item_banco is not None
    assert item_banco.medico_id == medico.id
    assert item_banco.triagem_id == triagem.id


def test_post_fila_sem_vaga_apresenta_aguardando_vaga(client, db_session):
    """Quando não há médico disponível, o item é gravado sem médico e com estado 'Aguardando vaga na especialidade'."""
    paciente = _criar_paciente(db_session)
    triagem = _criar_triagem(db_session, paciente.id, urgencia="media", especialidade="oftalmologia")
    # Não há nenhum médico oftalmologista cadastrado

    resposta = client.post("/fila", json={"triagem_id": triagem.id})
    assert resposta.status_code == 201

    dados = resposta.json()
    assert dados["triagem_id"] == triagem.id
    assert dados["medico_id"] is None
    assert dados["medico_alocado"] == AGUARDANDO_VAGA_NA_ESPECIALIDADE
    assert dados["medico_alocado"] == "Aguardando vaga na especialidade"
    assert dados["status"] == "aguardando"
    assert dados["score"] >= 30.0  # urgência media inicia em 30


def test_post_fila_distribui_cargas_e_respeita_capacidade(client, db_session):
    """
    Testa a alocação sequencial com múltiplos pacientes:
    - Médico 1 tem capacidade 1
    - Médico 2 tem capacidade 2
    Ao lotar, o próximo paciente fica 'Aguardando vaga na especialidade'.
    """
    medico1 = _criar_medico(db_session, nome="Dr. Bruno", especialidade="clinica_geral", capacidade_simultanea=1)
    medico2 = _criar_medico(db_session, nome="Dra. Camila", especialidade="clinica_geral", capacidade_simultanea=2)

    pacientes = [_criar_paciente(db_session, f"Paciente {i}", f"p{i}@example.com") for i in range(1, 5)]
    triagens = [_criar_triagem(db_session, p.id, especialidade="clinica_geral") for p in pacientes]

    # Inserção 1: Ambas cargas 0 -> desempata pelo menor ID (medico1)
    res1 = client.post("/fila", json={"triagem_id": triagens[0].id}).json()
    assert res1["medico_id"] == medico1.id
    assert res1["medico_alocado"] == "Dr. Bruno"

    # Inserção 2: medico1 está com carga 1 (capacidade 1 atingida); medico2 tem carga 0 -> escolhe medico2
    res2 = client.post("/fila", json={"triagem_id": triagens[1].id}).json()
    assert res2["medico_id"] == medico2.id
    assert res2["medico_alocado"] == "Dra. Camila"

    # Inserção 3: medico1 lotado; medico2 tem carga 1 < capacidade 2 -> escolhe medico2
    res3 = client.post("/fila", json={"triagem_id": triagens[2].id}).json()
    assert res3["medico_id"] == medico2.id
    assert res3["medico_alocado"] == "Dra. Camila"

    # Inserção 4: ambos lotados (medico1: 1/1, medico2: 2/2) -> Sem vaga!
    res4 = client.post("/fila", json={"triagem_id": triagens[3].id}).json()
    assert res4["medico_id"] is None
    assert res4["medico_alocado"] == "Aguardando vaga na especialidade"


def test_post_fila_triagem_inexistente_retorna_404(client):
    """Tentativa de inserir triagem inexistente deve retornar 404."""
    resposta = client.post("/fila", json={"triagem_id": 99999})
    assert resposta.status_code == 404
    assert "não encontrada" in resposta.json()["detail"].lower()


def test_post_fila_payload_invalido_retorna_422(client):
    """Payload sem triagem_id ou com valor inválido deve retornar 422."""
    assert client.post("/fila", json={}).status_code == 422
    assert client.post("/fila", json={"triagem_id": 0}).status_code == 422
    assert client.post("/fila", json={"triagem_id": -5}).status_code == 422


# ---------------------------------------------------------------------------
# Testes do GET /fila
# ---------------------------------------------------------------------------

def test_get_fila_vazia_retorna_lista_vazia(client):
    """Fila sem itens retorna 200 e lista vazia."""
    resposta = client.get("/fila")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_get_fila_retorna_itens_ordenados_por_pontuacao(client, db_session):
    """
    GET /fila deve retornar itens ordenados de forma decrescente por score (maior pontuação primeiro),
    contendo motivo e médico alocado.
    """
    p1 = _criar_paciente(db_session, "Ana", "ana@example.com")
    p2 = _criar_paciente(db_session, "Bernardo", "bernardo@example.com")
    p3 = _criar_paciente(db_session, "Carlos", "carlos@example.com")

    # Criamos triagens de urgências diferentes
    t_baixa = _criar_triagem(
        db_session, p1.id, urgencia="baixa", especialidade="clinica_geral",
        texto_sintomas="Gripe leve", justificativa="Caso sem gravidade",
    )
    t_emergencia = _criar_triagem(
        db_session, p2.id, urgencia="emergencia", especialidade="cardiologia",
        texto_sintomas="Parada iminente", justificativa="Emergência absoluta",
    )
    t_alta = _criar_triagem(
        db_session, p3.id, urgencia="alta", especialidade="cardiologia",
        texto_sintomas="Dor precordial intensa", justificativa="Alto risco",
    )

    medico = _criar_medico(db_session, nome="Dr. Ricardo", especialidade="cardiologia", capacidade_simultanea=5)

    # Inserimos na ordem: baixa, emergencia, alta
    client.post("/fila", json={"triagem_id": t_baixa.id})
    client.post("/fila", json={"triagem_id": t_emergencia.id})
    client.post("/fila", json={"triagem_id": t_alta.id})

    # Consulta a fila
    resposta = client.get("/fila")
    assert resposta.status_code == 200

    itens = resposta.json()
    assert len(itens) == 3

    # Ordenação esperada pelo score: emergencia (100) > alta (55) > baixa (10)
    assert itens[0]["triagem_id"] == t_emergencia.id
    assert itens[0]["score"] >= 100.0
    assert itens[0]["urgencia"] == "emergencia"
    assert itens[0]["motivo"] == "Emergência absoluta"
    assert itens[0]["medico_alocado"] == "Dr. Ricardo"
    assert itens[0]["paciente_nome"] == "Bernardo"

    assert itens[1]["triagem_id"] == t_alta.id
    assert itens[1]["score"] >= 55.0
    assert itens[1]["urgencia"] == "alta"
    assert itens[1]["motivo"] == "Alto risco"
    assert itens[1]["medico_alocado"] == "Dr. Ricardo"

    assert itens[2]["triagem_id"] == t_baixa.id
    assert itens[2]["score"] >= 10.0
    assert itens[2]["urgencia"] == "baixa"
    assert itens[2]["motivo"] == "Caso sem gravidade"
    # Sem médico de clínica geral disponível
    assert itens[2]["medico_alocado"] == "Aguardando vaga na especialidade"


def test_get_fila_apresenta_aguardando_vaga_quando_sem_medico(client, db_session):
    """Garante que a apresentação textual sem médico é 'Aguardando vaga na especialidade' na listagem."""
    paciente = _criar_paciente(db_session)
    triagem = _criar_triagem(db_session, paciente.id, especialidade="pediatria")

    client.post("/fila", json={"triagem_id": triagem.id})

    resposta = client.get("/fila")
    assert resposta.status_code == 200
    itens = resposta.json()
    assert len(itens) == 1
    assert itens[0]["medico_alocado"] == "Aguardando vaga na especialidade"
    assert itens[0]["medico_id"] is None


def test_get_fila_filtro_por_status(client, db_session):
    """GET /fila aceita filtro por status."""
    p1 = _criar_paciente(db_session, "P1", "p1@test.com")
    p2 = _criar_paciente(db_session, "P2", "p2@test.com")
    t1 = _criar_triagem(db_session, p1.id)
    t2 = _criar_triagem(db_session, p2.id)

    res1 = client.post("/fila", json={"triagem_id": t1.id}).json()
    res2 = client.post("/fila", json={"triagem_id": t2.id}).json()

    # Altera status do item 2 diretamente no banco para simular atendimento
    item2 = db_session.get(ItemFila, res2["id"])
    item2.status = "em_atendimento"
    db_session.commit()

    # Consulta filtrada por 'aguardando'
    res_aguardando = client.get("/fila?status=aguardando")
    assert res_aguardando.status_code == 200
    dados_aguardando = res_aguardando.json()
    assert len(dados_aguardando) == 1
    assert dados_aguardando[0]["id"] == res1["id"]

    # Consulta filtrada por 'em_atendimento'
    res_atendimento = client.get("/fila?status=em_atendimento")
    assert res_atendimento.status_code == 200
    dados_atendimento = res_atendimento.json()
    assert len(dados_atendimento) == 1
    assert dados_atendimento[0]["id"] == res2["id"]

