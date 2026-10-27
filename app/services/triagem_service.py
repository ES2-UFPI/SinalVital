from app.database.models.triagem import Triagem
from app.domain.triagem.factory import TriageClassifierFactory
from app.repositories.triagem_repository import TriagemRepository
from app.domain.triagem.strategies.classificador import ClassificadorFactory


class PacienteNaoEncontradoError(Exception):
    pass


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

        triagem = Triagem(
            paciente_id=paciente_id,
            relato=relato,
            estrategia=classificador.nome,
            classificacao=resultado.classificacao,
            prioridade=resultado.prioridade,
            urgencia=classificacao_detalhada["urgencia"],
            especialidade=classificacao_detalhada["especialidade"],
            justificativa=resultado.justificativa,
        )

        return self.repo.salvar(triagem)