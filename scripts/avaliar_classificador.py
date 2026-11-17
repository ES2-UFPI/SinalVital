"""Compara os classificadores em um conjunto de casos: python -m scripts.avaliar_classificador

Mede o mock (palavras-chave), o Claude sem exemplos (zero-shot) e o Claude com exemplos
(few-shot) nos mesmos casos de scripts/casos_avaliacao.json.

ATENÇÃO: os modos zero-shot e few-shot chamam a API da Anthropic e GASTAM CRÉDITO
(um pedido por caso, por modo). Exige ANTHROPIC_API_KEY no .env. O gabarito do arquivo de
casos é um RASCUNHO sem validação clínica: revise antes de apresentar os números.

Uso:
    python -m scripts.avaliar_classificador                  # mock + zero-shot + few-shot
    python -m scripts.avaliar_classificador --modos mock      # sem custo, sem chave
    python -m scripts.avaliar_classificador --modelo claude-haiku-5-5
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.domain.triagem.strategies.classificador import Classificador, MockClassificador
from app.domain.triagem.strategies.claude_classificador import ClaudeClassificador
from app.triagem.regras import NIVEIS

ARQUIVO_CASOS = Path(__file__).resolve().parent / "casos_avaliacao.json"
MODOS = ("mock", "zero-shot", "few-shot")


class _SemFallback(Classificador):
    """Na avaliação, uma falha da API deve aparecer como erro, nunca virar resposta do mock."""

    def classificar(self, texto_sintomas: str):
        raise RuntimeError("API indisponível (sem fallback na avaliação)")


def carregar_casos(caminho: Path = ARQUIVO_CASOS) -> list:
    return json.loads(caminho.read_text(encoding="utf-8"))["casos"]


def _gravidade(nivel: str) -> int:
    """0 = mais urgente (emergência) ... 3 = menos urgente (baixa)."""
    return NIVEIS.index(nivel)


def avaliar(classificador: Classificador, casos: list) -> dict:
    """Roda o classificador em cada caso e conta acertos, erros e desvios de urgência."""
    r = {"total": len(casos), "acertos_urgencia": 0, "acertos_especialidade": 0,
         "acertos_total": 0, "subtriagem": 0, "supertriagem": 0, "erros": 0, "divergencias": []}
    for caso in casos:
        try:
            saida = classificador.classificar(caso["relato"])
        except Exception as erro:  # a avaliação continua mesmo com falhas isoladas
            r["erros"] += 1
            r["divergencias"].append({**caso, "obtido": f"ERRO ({type(erro).__name__})"})
            continue
        certo_u = saida["urgencia"] == caso["urgencia"]
        certo_e = saida["especialidade"] == caso["especialidade"]
        r["acertos_urgencia"] += certo_u
        r["acertos_especialidade"] += certo_e
        r["acertos_total"] += certo_u and certo_e
        if _gravidade(saida["urgencia"]) > _gravidade(caso["urgencia"]):
            r["subtriagem"] += 1   # o modelo subestimou a gravidade: o erro mais perigoso
        elif _gravidade(saida["urgencia"]) < _gravidade(caso["urgencia"]):
            r["supertriagem"] += 1
        if not (certo_u and certo_e):
            r["divergencias"].append(
                {**caso, "obtido": f"{saida['urgencia']} / {saida['especialidade']}"}
            )
    return r


def _criar(modo: str, modelo: Optional[str]) -> Classificador:
    if modo == "mock":
        return MockClassificador()
    exemplos = () if modo == "zero-shot" else None
    return ClaudeClassificador(modelo=modelo, exemplos=exemplos, fallback=_SemFallback())


def _pct(parte: int, total: int) -> str:
    return f"{parte}/{total} ({100 * parte / total:.0f}%)"


def imprimir(resultados: dict) -> None:
    colunas = list(resultados)
    total = next(iter(resultados.values()))["total"]
    linhas = [
        ("Urgência correta", "acertos_urgencia"),
        ("Especialidade correta", "acertos_especialidade"),
        ("Ambas corretas", "acertos_total"),
        ("Subtriagem (subestimou)", "subtriagem"),
        ("Supertriagem (superestimou)", "supertriagem"),
        ("Falhas de API", "erros"),
    ]
    print(f"\n{'':30}" + "".join(f"{c:>16}" for c in colunas))
    for rotulo, chave in linhas:
        print(f"{rotulo:30}" + "".join(
            f"{_pct(resultados[c][chave], total):>16}" for c in colunas))
    print("\nSubtriagem é o erro mais grave: classificar como menos urgente do que deveria.")
    for modo, r in resultados.items():
        if r["divergencias"]:
            print(f"\n--- Divergências ({modo}) ---")
            for d in r["divergencias"]:
                print(f"  \"{d['relato']}\"\n    esperado: {d['urgencia']} / {d['especialidade']}"
                      f"  |  obtido: {d['obtido']}")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--modos", nargs="+", choices=MODOS, default=list(MODOS))
    parser.add_argument("--modelo", help="modelo Claude (padrão: ANTHROPIC_MODEL ou o do código)")
    args = parser.parse_args(argv)

    load_dotenv()
    usa_api = any(m != "mock" for m in args.modos)
    if usa_api and not os.getenv("ANTHROPIC_API_KEY", "").strip():
        print("ANTHROPIC_API_KEY ausente no .env. Use --modos mock para rodar sem chave.")
        return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    casos = carregar_casos()
    chamadas = len(casos) * sum(m != "mock" for m in args.modos)
    print(f"{len(casos)} casos; {chamadas} chamadas à API da Anthropic (consomem crédito).")
    resultados = {modo: avaliar(_criar(modo, args.modelo), casos) for modo in args.modos}
    imprimir(resultados)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
