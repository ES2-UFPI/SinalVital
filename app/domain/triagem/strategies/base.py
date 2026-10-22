from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoTriagem:
    classificacao: str   # ex.: "vermelho", "laranja", "amarelo", "verde", "azul"
    prioridade: int      # 1 (mais urgente) a 5
    justificativa: str


class TriageStrategy(ABC):
    nome: str

    @abstractmethod
    def classificar(self, relato: str) -> ResultadoTriagem:
        ...