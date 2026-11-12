from app.database.models.triagem import Triagem
from app.domain.triagem.factory import TriageClassifierFactory
from app.repositories.triagem_repository import TriagemRepository
from app.domain.triagem.strategies.classificador import ClassificadorFactory


class PacienteNaoEncontradoError(Exception):
    pass


MAPA_URGENCIA_CLASSIFICACAO = {
    "emergencia": ("vermelho", 1),
    "alta": ("laranja", 2),
    "media": ("amarelo", 3),
    "baixa": ("verde", 4),
}


class TriagemService:
    def __init__(self, repo: TriagemRepository):
        self.repo = repo

    def realizar_triagem(
        self, paciente_id: int, relato: str, estrategia: str
    ) -> Triagem:
        if not self.repo.paciente_existe(paciente_id):
            raise PacienteNaoEncontradoError(paciente_id)

        classificador = TriageClassifierFactory.criar(estrategia)
        resultado = classificador.classificar(relato)
        classificador_ia_mock = ClassificadorFactory.criar()
        classificacao_detalhada = classificador_ia_mock.classificar(relato)

        urgencia_final = classificacao_detalhada["urgencia"]
        classificacao_unificada, prioridade_unificada = (
            MAPA_URGENCIA_CLASSIFICACAO.get(
                urgencia_final,
                (resultado.classificacao, resultado.prioridade),
            )
        )

        triagem = Triagem(
            paciente_id=paciente_id,
            relato=relato,
            estrategia=classificador.nome,
            classificacao=classificacao_unificada,
            prioridade=prioridade_unificada,
            urgencia=urgencia_final,
            especialidade=classificacao_detalhada["especialidade"],
            justificativa=classificacao_detalhada.get("justificativa")
            or resultado.justificativa,
        )

        return self.repo.salvar(triagem)