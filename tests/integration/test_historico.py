"""
Testes do endpoint GET /pacientes/{paciente_id}/historico
=========================================================
Cobertura:
    1. 404 para paciente inexistente.
    2. Histórico vazio (paciente sem eventos).
    3. Eventos retornados em ordem cronológica ascendente.
    4. Filtro por tipo_evento funciona corretamente.
    5. Filtro por tipo_evento inexistente retorna lista vazia.
    6. Dados do paciente estão presentes na resposta.
    7. Todos os campos obrigatórios dos eventos estão presentes.
    8. Sem filtro retorna todos os tipos de evento.

Setup:
    Utiliza banco SQLite em memória via override de dependência (conftest.py),
    sem depender de arquivo de banco externo nem de variável de ambiente.
"""

from datetime import datetime, timedelta, timezone

from app.database.models.models import Paciente, EventoHistorico


# ---------------------------------------------------------------------------
# Helpers de inserção (reutilizados por todos os testes)
# ---------------------------------------------------------------------------

def _criar_paciente(db, nome="Ana Silva", email="ana@sinalvital.com", idade=40):
    """Insere um paciente no banco e retorna o id (int)."""
    paciente = Paciente(nome=nome, email=email, idade=idade)
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente.id


def _criar_evento(
    db,
    paciente_id: int,
    tipo_evento: str = "triagem",
    descricao: str = "Dor de cabeça leve",
    urgencia: str = "baixa",
    especialidade: str = "clinica_geral",
    delta_minutos: int = 0,
):
    """Insere um EventoHistorico com timestamp controlado (para testar ordenação)."""
    evento = EventoHistorico(
        paciente_id=paciente_id,
        tipo_evento=tipo_evento,
        descricao=descricao,
        urgencia=urgencia,
        especialidade=especialidade,
        criado_em=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        + timedelta(minutes=delta_minutos),
    )
    db.add(evento)
    db.commit()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestHistoricoPaciente:

    def test_paciente_inexistente_retorna_404(self, client):
        """Deve retornar 404 quando o paciente não existe no banco."""
        response = client.get("/pacientes/9999/historico")
        assert response.status_code == 404
        assert "não encontrado" in response.json()["detail"].lower()

    def test_historico_vazio_para_paciente_sem_eventos(self, client, db_session):
        """Paciente cadastrado mas sem eventos deve retornar lista vazia."""
        paciente_id = _criar_paciente(db_session)

        response = client.get(f"/pacientes/{paciente_id}/historico")
        assert response.status_code == 200

        data = response.json()
        assert data["eventos_historico"] == []

    def test_eventos_retornados_em_ordem_cronologica_ascendente(self, client, db_session):
        """
        Dado três eventos inseridos fora de ordem, a resposta deve trazê-los
        do mais antigo (+0 min) ao mais recente (+20 min).
        """
        paciente_id = _criar_paciente(db_session)

        # Insere em ordem inversa à esperada
        _criar_evento(db_session, paciente_id, descricao="Evento 3", delta_minutos=20)
        _criar_evento(db_session, paciente_id, descricao="Evento 1", delta_minutos=0)
        _criar_evento(db_session, paciente_id, descricao="Evento 2", delta_minutos=10)

        response = client.get(f"/pacientes/{paciente_id}/historico")
        assert response.status_code == 200

        eventos = response.json()["eventos_historico"]
        assert len(eventos) == 3
        descricoes = [e["descricao"] for e in eventos]
        assert descricoes == ["Evento 1", "Evento 2", "Evento 3"], (
            f"Ordem incorreta: {descricoes}"
        )

    def test_filtro_tipo_evento_triagem(self, client, db_session):
        """Filtro ?tipo_evento=triagem deve devolver apenas triagens."""
        paciente_id = _criar_paciente(db_session)
        _criar_evento(db_session, paciente_id, tipo_evento="triagem", delta_minutos=0)
        _criar_evento(db_session, paciente_id, tipo_evento="atendimento", delta_minutos=5)
        _criar_evento(db_session, paciente_id, tipo_evento="triagem", delta_minutos=10)

        response = client.get(
            f"/pacientes/{paciente_id}/historico?tipo_evento=triagem"
        )
        assert response.status_code == 200

        eventos = response.json()["eventos_historico"]
        assert len(eventos) == 2
        assert all(e["tipo_evento"] == "triagem" for e in eventos)

    def test_filtro_tipo_evento_atendimento(self, client, db_session):
        """Filtro ?tipo_evento=atendimento deve devolver apenas atendimentos."""
        paciente_id = _criar_paciente(db_session)
        _criar_evento(db_session, paciente_id, tipo_evento="triagem", delta_minutos=0)
        _criar_evento(db_session, paciente_id, tipo_evento="atendimento", delta_minutos=5)

        response = client.get(
            f"/pacientes/{paciente_id}/historico?tipo_evento=atendimento"
        )
        assert response.status_code == 200

        eventos = response.json()["eventos_historico"]
        assert len(eventos) == 1
        assert eventos[0]["tipo_evento"] == "atendimento"

    def test_filtro_tipo_inexistente_retorna_lista_vazia(self, client, db_session):
        """Filtro por tipo_evento inexistente deve retornar lista vazia (não 404)."""
        paciente_id = _criar_paciente(db_session)
        _criar_evento(db_session, paciente_id, tipo_evento="triagem")

        response = client.get(
            f"/pacientes/{paciente_id}/historico?tipo_evento=nao_existe"
        )
        assert response.status_code == 200
        assert response.json()["eventos_historico"] == []

    def test_dados_do_paciente_presentes_na_resposta(self, client, db_session):
        """A resposta deve incluir os dados cadastrais do paciente."""
        paciente_id = _criar_paciente(
            db_session,
            nome="Carlos Melo",
            email="carlos@sinalvital.com",
            idade=55,
        )

        response = client.get(f"/pacientes/{paciente_id}/historico")
        assert response.status_code == 200

        data = response.json()
        assert data["nome"] == "Carlos Melo"
        assert data["email"] == "carlos@sinalvital.com"
        assert data["idade"] == 55

    def test_campos_obrigatorios_nos_eventos(self, client, db_session):
        """Cada evento deve conter os campos exigidos pelo schema."""
        campos_esperados = {
            "id", "paciente_id", "tipo_evento", "descricao",
            "urgencia", "especialidade", "criado_em",
        }

        paciente_id = _criar_paciente(db_session)
        _criar_evento(
            db_session,
            paciente_id,
            tipo_evento="triagem",
            descricao="Falta de ar",
            urgencia="alta",
            especialidade="cardiologia",
        )

        response = client.get(f"/pacientes/{paciente_id}/historico")
        assert response.status_code == 200

        evento = response.json()["eventos_historico"][0]
        campos_faltando = campos_esperados - evento.keys()
        assert not campos_faltando, f"Campos ausentes: {campos_faltando}"

    def test_sem_filtro_retorna_todos_os_tipos(self, client, db_session):
        """Sem filtro, todos os tipos de evento devem ser retornados."""
        paciente_id = _criar_paciente(db_session)
        _criar_evento(db_session, paciente_id, tipo_evento="triagem", delta_minutos=0)
        _criar_evento(db_session, paciente_id, tipo_evento="atendimento", delta_minutos=5)
        _criar_evento(db_session, paciente_id, tipo_evento="monitoramento", delta_minutos=10)

        response = client.get(f"/pacientes/{paciente_id}/historico")
        assert response.status_code == 200

        eventos = response.json()["eventos_historico"]
        assert len(eventos) == 3
        tipos = {e["tipo_evento"] for e in eventos}
        assert tipos == {"triagem", "atendimento", "monitoramento"}
