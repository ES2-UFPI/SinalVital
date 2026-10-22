from app.domain.triagem.strategies.base import ResultadoTriagem, TriageStrategy

REGRAS = [
    ("vermelho", 1, ["parada cardíaca", "inconsciente", "convulsão", "sem respirar", "hemorragia"]),
    ("laranja", 2, ["dor no peito", "falta de ar", "avc", "dificuldade para respirar"]),
    ("amarelo", 3, ["febre alta", "vômito", "dor intensa", "fratura"]),
    ("verde", 4, ["febre", "dor de cabeça", "tosse", "diarreia"]),
]


class PalavrasChaveStrategy(TriageStrategy):
    nome = "palavras_chave"

    def classificar(self, relato: str) -> ResultadoTriagem:
        texto = relato.lower()
        for classificacao, prioridade, termos in REGRAS:
            encontrados = [t for t in termos if t in texto]
            if encontrados:
                return ResultadoTriagem(
                    classificacao=classificacao,
                    prioridade=prioridade,
                    justificativa=f"Termos identificados: {', '.join(encontrados)}",
                )
        return ResultadoTriagem(
            classificacao="azul",
            prioridade=5,
            justificativa="Nenhum sinal de alerta identificado no relato.",
        )