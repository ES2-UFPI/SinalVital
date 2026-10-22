"""Compatibilidade: implementação em app.domain.triagem.strategies."""
from app.domain.triagem.strategies.classificador import (
    Classificador, ClassificadorFactory, MockClassificador, ResultadoClassificacao, load_dotenv,
)
