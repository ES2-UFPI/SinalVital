"""Contrato e seleção dos classificadores de sintomas (issue #15)."""

import os
from abc import ABC, abstractmethod
from typing import Literal, TypedDict

from dotenv import load_dotenv

from app.triagem.regras import classificar_texto


class ResultadoClassificacao(TypedDict):
    urgencia: Literal["emergencia", "alta", "media", "baixa"]
    especialidade: str
    justificativa: str


class Classificador(ABC):
    """Strategy: contrato comum para os algoritmos de classificação."""

    @abstractmethod
    def classificar(self, texto_sintomas: str) -> ResultadoClassificacao:
        """Classifica um relato e retorna urgência, especialidade e justificativa."""
        raise NotImplementedError


class MockClassificador(Classificador):
    """Simulação determinística, sem serviços externos; usa as regras de app.triagem.regras."""

    def classificar(self, texto_sintomas: str) -> ResultadoClassificacao:
        if not (texto_sintomas or "").strip():
            raise ValueError("O relato de sintomas não pode estar vazio.")
        resultado = classificar_texto(texto_sintomas)
        return {"urgencia": resultado.urgencia, "especialidade": resultado.especialidade,
                "justificativa": resultado.justificativa}


class ClassificadorFactory:
    """Factory: concentra a escolha da Strategy pela configuração MODO_IA."""

    @staticmethod
    def criar() -> Classificador:
        # Lê a configuração a cada criação; variáveis do ambiente prevalecem sobre .env.
        load_dotenv()
        modo = os.getenv("MODO_IA", "mock").strip().lower()
        if modo not in {"mock", "real"}:
            raise ValueError("MODO_IA inválido. Use 'mock' ou 'real'.")
        # Fallback previsto na issue: ainda não há Strategy real na aplicação principal.
        return MockClassificador()
