from app.domain.triagem.strategies.base import TriageStrategy
from app.domain.triagem.strategies.palavras_chave import PalavrasChaveStrategy


class EstrategiaInvalidaError(ValueError):
    pass


class TriageClassifierFactory:
    _registry: dict[str, type[TriageStrategy]] = {
        PalavrasChaveStrategy.nome: PalavrasChaveStrategy,
    }

    @classmethod
    def registrar(cls, strategy: type[TriageStrategy]) -> None:
        cls._registry[strategy.nome] = strategy

    @classmethod
    def criar(cls, nome: str = "palavras_chave") -> TriageStrategy:
        try:
            return cls._registry[nome]()
        except KeyError:
            disponiveis = ", ".join(cls._registry)
            raise EstrategiaInvalidaError(
                f"Estratégia '{nome}' inválida. Disponíveis: {disponiveis}"
            )
