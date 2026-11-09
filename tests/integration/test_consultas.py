"""
Testes em TDD (Issue #46 — [002-01]) para registro de consulta médica
=====================================================================
Cobertura exigida pela história da Dra. Helena (PB-002 — Prontuário Cumulativo):
    1. POST /consultas recebe paciente_id, medico_id, diagnostico e conduta (e anamnese opcional) e retorna 201.
    2. Ao salvar a consulta, cria automaticamente um EventoHistorico com tipo_evento="consulta".
    3. O evento salvo aparece imediatamente em GET /pacientes/{id}/historico (e no filtro ?tipo_evento=consulta).
    4. Caráter cumulativo: novas consultas não sobrescrevem triagens nem consultas anteriores.
    5. Validações de erro:
       - Paciente inexistente retorna 404 e não grava evento.
       - Médico inexistente retorna 404 e não grava evento.
       - Campos obrigatórios vazios (ou só espaços) / ausentes retornam 422 e não gravam evento.
"""

import pytest

from app.database.models import EventoHistorico, Paciente


# ---------------------------------------------------------------------------
# Helpers de preparação de dados no banco em memória
# ---------------------------------------------------------------------------

def _criar_paciente(
    db,
    nome: str = "Raimundo Nonato",
    email: str = "raimundo@sinalvital.com",
    idade: int = 65,
    condicao_cronica: str = "Cardiopatia e hipertensão",
) -> int:
    paciente = Paciente(
        nome=nome,
        email=email,
        idade=idade,
        condicao_cronica=condicao_cronica,
    )
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente.id


def _criar_medico(
    db,
    nome: str = "Dra. Helena Costa",
    especialidade: str = "cardiologia",
    capacidade_simultanea: int = 3,
    ativo: bool = True,
) -> int:
    from app.database.models import Medico

    medico = Medico(
        nome=nome,
        especialidade=especialidade,
        capacidade_simultanea=capacidade_simultanea,
        ativo=ativo,
    )
    db.add(medico)
    db.commit()
    db.refresh(medico)
    return medico.id


# ---------------------------------------------------------------------------
# Casos de Teste — Registro de Consulta e Prontuário Cumulativo
# ---------------------------------------------------------------------------

class TestRegistroConsulta:

    def test_registrar_consulta_retorna_201_com_campos_esperados(self, client, db_session):
        """POST /consultas deve aceitar paciente_id, medico_id, diagnostico e conduta e retornar 201."""
        paciente_id = _criar_paciente(db_session)
        medico_id = _criar_medico(db_session)

        payload = {
            "paciente_id": paciente_id,
            "medico_id": medico_id,
            "diagnostico": "Hipertensão arterial sistêmica controlada",
            "conduta": "Manter losartana 50mg/dia e agendar retorno em 90 dias",
        }
        response = client.post("/consultas", json=payload)

        assert response.status_code == 201
        dados = response.json()
        assert dados["id"] is not None
        assert dados["paciente_id"] == paciente_id
        assert dados["medico_id"] == medico_id
        assert dados["diagnostico"] == payload["diagnostico"]
        assert dados["conduta"] == payload["conduta"]
        assert dados["criado_em"] is not None

    def test_registrar_consulta_aceita_anamnese_opcional(self, client, db_session):
        """POST /consultas também deve aceitar o campo opcional de anamnese quando informado."""
        paciente_id = _criar_paciente(db_session)
        medico_id = _criar_medico(db_session)

        payload = {
            "paciente_id": paciente_id,
            "medico_id": medico_id,
            "anamnese": "Paciente relata boa adesão medicamentosa, nega dor torácica na última semana.",
            "diagnostico": "Angina estável em acompanhamento",
            "conduta": "Manter medicação atual e monitorar pressão arterial",
        }
        response = client.post("/consultas", json=payload)

        assert response.status_code == 201
        assert response.json()["anamnese"] == payload["anamnese"]

    def test_salvar_consulta_cria_evento_historico_tipo_consulta(self, client, db_session):
        """Ao gravar uma consulta, deve existir um registro em eventos_historico com tipo_evento='consulta'."""
        paciente_id = _criar_paciente(db_session)
        medico_id = _criar_medico(db_session, especialidade="cardiologia")

        response = client.post(
            "/consultas",
            json={
                "paciente_id": paciente_id,
                "medico_id": medico_id,
                "diagnostico": "Arritmia sinusal leve",
                "conduta": "Solicitar holter 24h e retorno após exame",
            },
        )
        assert response.status_code == 201

        eventos = (
            db_session.query(EventoHistorico)
            .filter(EventoHistorico.paciente_id == paciente_id)
            .all()
        )
        assert len(eventos) == 1
        evento = eventos[0]
        assert evento.tipo_evento == "consulta"
        assert evento.especialidade == "cardiologia"
        assert "Arritmia sinusal leve" in evento.descricao
        assert "Solicitar holter 24h" in evento.descricao

    def test_consulta_aparece_no_get_historico_do_paciente(self, client, db_session):
        """A consulta salva deve aparecer imediatamente em GET /pacientes/{id}/historico e no filtro ?tipo_evento=consulta."""
        paciente_id = _criar_paciente(db_session)
        medico_id = _criar_medico(db_session, especialidade="cardiologia")

        post_resp = client.post(
            "/consultas",
            json={
                "paciente_id": paciente_id,
                "medico_id": medico_id,
                "diagnostico": "Insuficiência cardíaca compensada",
                "conduta": "Restrição hídrica moderada e manutenção da prescrição",
            },
        )
        assert post_resp.status_code == 201

        hist_resp = client.get(f"/pacientes/{paciente_id}/historico")
        assert hist_resp.status_code == 200
        eventos = hist_resp.json()["eventos_historico"]
        assert len(eventos) == 1
        assert eventos[0]["tipo_evento"] == "consulta"
        assert eventos[0]["especialidade"] == "cardiologia"
        assert "Insuficiência cardíaca compensada" in eventos[0]["descricao"]
        assert "Restrição hídrica moderada" in eventos[0]["descricao"]

        filtro_resp = client.get(f"/pacientes/{paciente_id}/historico?tipo_evento=consulta")
        assert filtro_resp.status_code == 200
        assert len(filtro_resp.json()["eventos_historico"]) == 1

    def test_prontuario_cumulativo_nao_sobrescreve_eventos_anteriores(self, client, db_session):
        """Múltiplas consultas e triagens devem se acumular no histórico sem sobrescrever atendimentos passados."""
        paciente_id = _criar_paciente(db_session)
        medico_id = _criar_medico(db_session)

        client.post(
            f"/pacientes/{paciente_id}/triagens",
            json={"relato": "Falta de ar aos esforços", "estrategia": "palavras_chave"},
        )
        r1 = client.post(
            "/consultas",
            json={
                "paciente_id": paciente_id,
                "medico_id": medico_id,
                "diagnostico": "Primeira avaliação cardiológica",
                "conduta": "Solicitado ecocardiograma",
            },
        )
        r2 = client.post(
            "/consultas",
            json={
                "paciente_id": paciente_id,
                "medico_id": medico_id,
                "diagnostico": "Retorno com ecocardiograma normal",
                "conduta": "Alta ambulatorial com acompanhamento semestral",
            },
        )

        assert r1.status_code == 201
        assert r2.status_code == 201

        hist_resp = client.get(f"/pacientes/{paciente_id}/historico")
        assert hist_resp.status_code == 200
        eventos = hist_resp.json()["eventos_historico"]
        assert len(eventos) == 3
        tipos = [e["tipo_evento"] for e in eventos]
        assert tipos.count("triagem") == 1
        assert tipos.count("consulta") == 2


# ---------------------------------------------------------------------------
# Casos de Teste — Validações (Paciente/Médico inexistentes e Campos Vazios)
# ---------------------------------------------------------------------------

class TestValidacoesConsulta:

    def test_paciente_inexistente_retorna_404_sem_gravar_evento(self, client, db_session):
        """Deve retornar 404 se paciente_id não existir no banco."""
        medico_id = _criar_medico(db_session)

        response = client.post(
            "/consultas",
            json={
                "paciente_id": 9999,
                "medico_id": medico_id,
                "diagnostico": "Diagnóstico válido",
                "conduta": "Conduta válida",
            },
        )

        assert response.status_code == 404
        assert "paciente" in response.json()["detail"].lower()
        assert db_session.query(EventoHistorico).count() == 0

    def test_medico_inexistente_retorna_404_sem_gravar_evento(self, client, db_session):
        """Deve retornar 404 se medico_id não existir no banco."""
        paciente_id = _criar_paciente(db_session)

        response = client.post(
            "/consultas",
            json={
                "paciente_id": paciente_id,
                "medico_id": 9999,
                "diagnostico": "Diagnóstico válido",
                "conduta": "Conduta válida",
            },
        )

        assert response.status_code == 404
        detalhe = response.json()["detail"].lower()
        assert "médico" in detalhe or "medico" in detalhe
        assert db_session.query(EventoHistorico).count() == 0

    @pytest.mark.parametrize(
        "campo_invalido",
        [
            {"diagnostico": ""},
            {"diagnostico": "    "},
            {"conduta": ""},
            {"conduta": "    "},
            {"anamnese": "   "},
            {"paciente_id": 0},
            {"medico_id": 0},
        ],
    )
    def test_campos_vazios_ou_invalidos_retornam_422(self, client, db_session, campo_invalido):
        """Campos vazios, apenas com espaços em branco ou IDs inválidos devem retornar 422."""
        payload = {
            "paciente_id": 1,
            "medico_id": 1,
            "diagnostico": "Hipertensão controlada",
            "conduta": "Manter medicação",
            **campo_invalido,
        }
        response = client.post("/consultas", json=payload)

        assert response.status_code == 422
        assert db_session.query(EventoHistorico).count() == 0

    @pytest.mark.parametrize("campo_ausente", ["paciente_id", "medico_id", "diagnostico", "conduta"])
    def test_campos_obrigatorios_ausentes_retornam_422(self, client, db_session, campo_ausente):
        """A ausência de qualquer campo obrigatório deve retornar 422."""
        payload = {
            "paciente_id": 1,
            "medico_id": 1,
            "diagnostico": "Hipertensão controlada",
            "conduta": "Manter medicação",
        }
        payload.pop(campo_ausente)

        response = client.post("/consultas", json=payload)

        assert response.status_code == 422
        assert db_session.query(EventoHistorico).count() == 0
