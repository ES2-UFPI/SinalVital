from app.domain.triagem.strategies.base import ResultadoTriagem, TriageStrategy
from app.triagem.regras import encontrar_termos, normalizar

# Demonstração, sem validação clínica. A busca ignora caixa e acentos e desconsidera
# termos negados ("sem dor no peito"); ver app/triagem/regras.py.
REGRAS = [
    ("vermelho", 1, ["parada cardíaca", "inconsciente", "convulsão", "sem respirar", "hemorragia",
                     "sangramento intenso", "desmaio", "desmaiei", "desmaiou", "perda de consciência", "dor no peito",
                     "dor forte no peito", "aperto no peito", "pressão no peito"]),
    ("laranja", 2, [ 
                    "falta de ar", "avc", "dificuldade para respirar", "não consigo respirar",
                    "paralisia", "fala arrastada", "perda de visão", "perda súbita de visão", "tontura"]),
    ("amarelo", 3, ["febre alta", "vômito", "dor intensa", "fratura"]),
    ("verde", 4, ["febre", "dor de cabeça", "tosse", "diarreia"]),
]


class PalavrasChaveStrategy(TriageStrategy):
    nome = "palavras_chave"

    def classificar(self, relato: str) -> ResultadoTriagem:
        for classificacao, prioridade, termos in REGRAS:
            exibicao = {normalizar(t): t for t in termos}
            encontrados = encontrar_termos(relato, tuple(termos))
            if encontrados:
                return ResultadoTriagem(
                    classificacao=classificacao,
                    prioridade=prioridade,
                    justificativa=f"Termos identificados: {', '.join(exibicao[t] for t in encontrados)}",
                )
        return ResultadoTriagem(
            classificacao="azul",
            prioridade=5,
            justificativa="Nenhum sinal de alerta identificado no relato.",
        )
