"""Contrato e seleção dos classificadores de sintomas (issue #15)."""

import os
from abc import ABC, abstractmethod
from typing import Literal, TypedDict

from dotenv import load_dotenv


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
    """Simulação inicial e determinística, sem acesso a serviços externos."""

    def classificar(self, texto_sintomas: str) -> ResultadoClassificacao:
        texto = texto_sintomas.strip().lower()
        if not texto:
            raise ValueError("O relato de sintomas não pode estar vazio.")

        termos = [termo for termo in ("dor no peito", "falta de ar") if termo in texto]
        if termos:
            urgencia = "emergencia"
        else:
            termos = [termo for termo in ("febre", "dor forte") if termo in texto]
            urgencia = "alta" if termos else "baixa"

        if "peito" in texto or "coração" in texto:
            especialidade = "cardiologia"
        elif "pele" in texto or "mancha" in texto:
            especialidade = "dermatologia"
        else:
            especialidade = "clinica_geral"

        justificativa = (
            f"Classificado como {urgencia} por mencionar: {', '.join(termos)}."
            if termos else
            "Classificado como baixa pelas regras iniciais do mock, sem palavras-chave de maior urgência."
        )
        return {"urgencia": urgencia, "especialidade": especialidade,
                "justificativa": justificativa}


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
