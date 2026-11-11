"""
Testes em TDD (Issue #47 — [002-02]) para o Painel Médico da Dra. Helena
========================================================================
Cobertura:
    1. Rota e estrutura HTML acessível de GET /pages/medico.html
       (semântica, controles de leitura, fila priorizada e formulário clínico).
    2. Navegação consistente (data-nav="medico") em todas as páginas do frontend.
    3. Integração JavaScript em /assets/js/app.js (/medicos, /fila, /consultas,
       consulta-form, fila-medica, Feedback.sucesso e Feedback.erro).
    4. Fluxo integrado End-to-End do Painel Médico via API (listagem de médicos,
       fila ordenada por score com alocação da Dra. Helena, registro de consulta
       com anamnese/diagnóstico/conduta refletido em GET /pacientes/{id}/historico?tipo_evento=consulta
       e tratamento de erros 404/422).
"""

import pytest

from app.database.models import Medico


# ---------------------------------------------------------------------------
# 1. Rota e Estrutura HTML Acessível (GET /pages/medico.html)
# ---------------------------------------------------------------------------

class TestEstruturaPainelMedicoHTML:

    def test_rota_medico_html_retorna_200_e_estrutura_basica(self, client):
        """GET /pages/medico.html deve retornar 200, text/html, doctype e lang pt-BR."""
        response = client.get("/pages/medico.html")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        html = response.text
        assert "<!doctype html>" in html.lower()
        assert 'lang="pt-BR"' in html
        assert 'data-page="medico"' in html

    def test_acessibilidade_landmark_skip_link_e_controles_leitura(self, client):
        """A página deve possuir link de salto .skip, main#conteudo e controles A-/A+/contraste."""
        html = client.get("/pages/medico.html").text

        assert 'class="skip"' in html
        assert 'href="#conteudo"' in html
        assert '<main id="conteudo" tabindex="-1">' in html
        assert 'id="font-down"' in html
        assert 'id="font-up"' in html
        assert 'id="contrast"' in html

    def test_assets_css_e_js_carregados_na_ordem_correta(self, client):
        """Deve carregar base.css, feedback.css, feedback.js e app.js (feedback.js antes de app.js)."""
        html = client.get("/pages/medico.html").text

        assert "/assets/css/base.css" in html
        assert "/assets/css/feedback.css" in html
        assert "/assets/js/feedback.js" in html
        assert "/assets/js/app.js" in html
        assert html.index("/assets/js/feedback.js") < html.index("/assets/js/app.js")

    def test_secao_fila_priorizada_de_atendimento_presente(self, client):
        """Deve conter a área da fila priorizada (#fila-medica), botão #atualizar-fila e seletor #medico-id."""
        html = client.get("/pages/medico.html").text

        assert 'id="fila-medica"' in html
        assert 'id="atualizar-fila"' in html
        assert 'id="medico-id"' in html

    def test_formulario_clinico_de_consulta_e_regioes_aria_live(self, client):
        """Deve conter #consulta-form com campos clínicos e regiões de feedback acessíveis."""
        html = client.get("/pages/medico.html").text

        assert 'id="consulta-form"' in html
        assert 'id="paciente-id"' in html
        assert 'id="medico-id"' in html
        assert 'id="anamnese"' in html
        assert 'id="diagnostico"' in html
        assert 'id="conduta"' in html
        assert 'id="feedback"' in html
        assert 'role="status"' in html
        assert 'aria-live="polite"' in html
        assert 'id="consulta-resultado"' in html


# ---------------------------------------------------------------------------
# 2. Navegação Consistente em Todas as Páginas
# ---------------------------------------------------------------------------

class TestNavegacaoPainelMedico:

    @pytest.mark.parametrize(
        "pagina",
        [
            "/",
            "/pages/cadastro.html",
            "/pages/triagem.html",
            "/pages/historico.html",
            "/pages/medico.html",
        ],
    )
    def test_todas_as_paginas_possuem_link_para_painel_medico(self, client, pagina):
        """Todas as páginas devem incluir o link para /pages/medico.html com data-nav='medico'."""
        response = client.get(pagina)

        assert response.status_code == 200
        assert 'href="/pages/medico.html"' in response.text
        assert 'data-nav="medico"' in response.text


# ---------------------------------------------------------------------------
# 3. Integração JavaScript (frontend/assets/js/app.js)
# ---------------------------------------------------------------------------

class TestIntegracaoJavaScriptPainelMedico:

    def test_app_js_contem_logica_do_painel_medico(self, client):
        """app.js deve integrar /medicos, /fila e /consultas, manipular DOM do painel e usar Feedback."""
        response = client.get("/assets/js/app.js")

        assert response.status_code == 200
        js = response.text
        assert "/medicos" in js
        assert "/fila" in js
        assert "/consultas" in js
        assert "consulta-form" in js
        assert "fila-medica" in js
        assert "Feedback.sucesso" in js
        assert "Feedback.erro" in js


# ---------------------------------------------------------------------------
# 4. Fluxo Integrado End-to-End do Painel Médico via API
# ---------------------------------------------------------------------------

class TestFluxoEndToEndPainelMedico:

    def test_fluxo_completo_painel_dra_helena_fila_priorizada_e_consulta_no_historico(
        self, client, db_session
    ):
        """
        Simula a jornada completa da Dra. Helena no painel médico:
        1. Cadastra a médica Dra. Helena (cardiologia) e verifica GET /medicos.
        2. Cadastra dois pacientes e realiza duas triagens cardiológicas (baixa vs alta urgência).
        3. Insere ambos na fila (POST /fila) e verifica em GET /fila que o paciente de
           urgência 'alta' aparece primeiro (maior score) alocado para 'Dra. Helena'.
        4. Registra a consulta clínica (POST /consultas) com anamnese, diagnóstico e conduta.
        5. Verifica que o atendimento aparece imediatamente em
           GET /pacientes/{id}/historico?tipo_evento=consulta com diagnóstico e conduta.
        """
        # 1. Cria a Dra. Helena (cardiologia) e valida listagem em GET /medicos
        dra_helena = Medico(
            nome="Dra. Helena",
            especialidade="cardiologia",
            capacidade_simultanea=3,
            ativo=True,
        )
        db_session.add(dra_helena)
        db_session.commit()
        db_session.refresh(dra_helena)

        medicos_resp = client.get("/medicos")
        assert medicos_resp.status_code == 200
        lista_medicos = medicos_resp.json()
        assert any(
            m["id"] == dra_helena.id and m["nome"] == "Dra. Helena"
            for m in lista_medicos
        )

        # 2. Cadastra dois pacientes
        p_baixa_resp = client.post(
            "/pacientes",
            json={
                "nome": "Carlos Rotina",
                "email": "carlos.rotina@sinalvital.com",
                "idade": 42,
            },
        )
        assert p_baixa_resp.status_code == 201
        paciente_baixa_id = p_baixa_resp.json()["id"]

        p_alta_resp = client.post(
            "/pacientes",
            json={
                "nome": "Raimundo Nonato",
                "email": "raimundo.nonato@sinalvital.com",
                "idade": 68,
                "condicao_cronica": "Hipertensão arterial",
            },
        )
        assert p_alta_resp.status_code == 201
        paciente_alta_id = p_alta_resp.json()["id"]

        # 3. Realiza duas triagens cardiológicas com urgências diferentes (baixa e alta)
        triagem_baixa_resp = client.post(
            f"/pacientes/{paciente_baixa_id}/triagens",
            json={
                "relato": "Acompanhamento de rotina do coração",
                "estrategia": "palavras_chave",
            },
        )
        assert triagem_baixa_resp.status_code == 201
        triagem_baixa = triagem_baixa_resp.json()
        assert triagem_baixa["urgencia"] == "baixa"
        assert triagem_baixa["especialidade"] == "cardiologia"

        triagem_alta_resp = client.post(
            f"/pacientes/{paciente_alta_id}/triagens",
            json={
                "relato": "Estou com palpitações e pressão alta desde cedo",
                "estrategia": "palavras_chave",
            },
        )
        assert triagem_alta_resp.status_code == 201
        triagem_alta = triagem_alta_resp.json()
        assert triagem_alta["urgencia"] == "alta"
        assert triagem_alta["especialidade"] == "cardiologia"

        # 4. Insere ambas na fila (baixa primeiro, alta depois) e verifica ordenação por score
        fila_1 = client.post("/fila", json={"triagem_id": triagem_baixa["id"]})
        assert fila_1.status_code == 201

        fila_2 = client.post("/fila", json={"triagem_id": triagem_alta["id"]})
        assert fila_2.status_code == 201

        fila_resp = client.get("/fila")
        assert fila_resp.status_code == 200
        itens_fila = fila_resp.json()
        assert len(itens_fila) == 2

        primeiro, segundo = itens_fila[0], itens_fila[1]
        assert primeiro["paciente_id"] == paciente_alta_id
        assert primeiro["urgencia"] == "alta"
        assert primeiro["score"] > segundo["score"]
        assert primeiro["medico_id"] == dra_helena.id
        assert primeiro["medico_alocado"] == "Dra. Helena"

        # 5. Dra. Helena registra a consulta clínica do paciente prioritário
        payload_consulta = {
            "paciente_id": paciente_alta_id,
            "medico_id": dra_helena.id,
            "anamnese": "Paciente refere palpitações há 4 horas, PA 160x100 mmHg.",
            "diagnostico": "Pico hipertensivo com taquicardia sinusal",
            "conduta": "Ajuste de anti-hipertensivo, ECG em repouso e retorno em 7 dias",
        }
        consulta_resp = client.post("/consultas", json=payload_consulta)
        assert consulta_resp.status_code == 201
        dados_consulta = consulta_resp.json()
        assert dados_consulta["paciente_id"] == paciente_alta_id
        assert dados_consulta["medico_id"] == dra_helena.id
        assert dados_consulta["anamnese"] == payload_consulta["anamnese"]
        assert dados_consulta["diagnostico"] == payload_consulta["diagnostico"]
        assert dados_consulta["conduta"] == payload_consulta["conduta"]

        # 6. Comprova que a consulta aparece imediatamente no histórico filtrado
        hist_resp = client.get(
            f"/pacientes/{paciente_alta_id}/historico?tipo_evento=consulta"
        )
        assert hist_resp.status_code == 200
        eventos_consulta = hist_resp.json()["eventos_historico"]
        assert len(eventos_consulta) == 1
        evento = eventos_consulta[0]
        assert evento["tipo_evento"] == "consulta"
        assert evento["especialidade"] == "cardiologia"
        assert payload_consulta["diagnostico"] in evento["descricao"]
        assert payload_consulta["conduta"] in evento["descricao"]

    def test_erros_404_e_422_no_envio_de_consulta_invalida(self, client, db_session):
        """Valida respostas 404 (paciente/médico inexistente) e 422 (campos inválidos) no painel."""
        dra_helena = Medico(
            nome="Dra. Helena",
            especialidade="cardiologia",
            capacidade_simultanea=2,
            ativo=True,
        )
        db_session.add(dra_helena)
        db_session.commit()
        db_session.refresh(dra_helena)

        # Paciente inexistente -> 404
        resp_404 = client.post(
            "/consultas",
            json={
                "paciente_id": 99999,
                "medico_id": dra_helena.id,
                "diagnostico": "Avaliação clínica",
                "conduta": "Orientação geral",
            },
        )
        assert resp_404.status_code == 404

        # Campos obrigatórios em branco -> 422
        resp_422 = client.post(
            "/consultas",
            json={
                "paciente_id": 1,
                "medico_id": dra_helena.id,
                "diagnostico": "   ",
                "conduta": "",
            },
        )
        assert resp_422.status_code == 422
