"""Regras de classificação por palavras-chave usadas pelo MockClassificador (issue #14).

Dicionários de DEMONSTRAÇÃO, sem validação clínica. O sistema não faz diagnóstico
e não substitui o SAMU (192). Em dúvida, o resultado deve subir de nível, nunca
descer. Os dicionários devem ser revisados pelo time/Product Owner.

Valores de urgência: emergencia > alta > media > baixa (ordem do motor de fila).
Especialidades: cardiologia, oftalmologia, dermatologia, clinica_geral.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Tuple

NIVEIS = ("emergencia", "alta", "media", "baixa")  # do mais ao menos urgente
ROTULO_NIVEL = {"emergencia": "emergência", "alta": "alta", "media": "média", "baixa": "baixa"}
ROTULO_ESPECIALIDADE = {"cardiologia": "cardiologia", "oftalmologia": "oftalmologia",
                        "dermatologia": "dermatologia", "clinica_geral": "clínica geral"}
ESPECIALIDADE_PADRAO = "clinica_geral"
URGENCIA_PADRAO = "baixa"

# Termos SEM acento e em minúsculas (o texto é normalizado antes da busca).
TERMOS_URGENCIA: Dict[str, Tuple[str, ...]] = {
    "emergencia": (
        "dor no peito", "dor forte no peito", "aperto no peito", "pressao no peito",
        "falta de ar", "nao consigo respirar", "dificuldade para respirar",
        "desmaio", "desmaiei", "desmaiou", "perda de consciencia", "convulsao",
        "hemorragia", "sangramento intenso", "paralisia", "fala arrastada",
        "perda subita de visao", "perda de visao", "produto quimico no olho",
    ),
    "alta": (
        "febre alta", "febre", "dor forte", "vomito", "vomitos", "tontura",
        "palpitacao", "palpitacoes", "inchaco nas pernas", "pressao alta",
        "visao turva", "visao embacada", "visao dupla", "dor no olho",
        "sensibilidade a luz",
    ),
    "media": (
        "tosse", "dor de garganta", "dor de cabeca", "dor nas costas", "diarreia",
        "nausea", "olho vermelho", "olho seco", "olhos secos", "coceira nos olhos",
        "ardencia nos olhos", "cansaco",
    ),
}

TERMOS_ESPECIALIDADE: Dict[str, Tuple[str, ...]] = {
    "cardiologia": (
        "peito", "coracao", "palpitacao", "palpitacoes", "pressao alta", "taquicardia",
        "falta de ar", "inchaco nas pernas", "cansaco",
    ),
    "oftalmologia": (
        "olho", "olhos", "visao", "vista", "colirio", "ocular", "palpebra",
    ),
    "dermatologia": ("pele", "mancha", "manchas", "erupcao"),
}

# Como o termo aparece na justificativa (com acento); os demais saem como no dicionário.
EXIBICAO = {
    "pressao no peito": "pressão no peito", "nao consigo respirar": "não consigo respirar",
    "perda de consciencia": "perda de consciência", "convulsao": "convulsão",
    "perda subita de visao": "perda súbita de visão", "perda de visao": "perda de visão",
    "produto quimico no olho": "produto químico no olho", "vomito": "vômito",
    "vomitos": "vômitos", "palpitacao": "palpitação", "palpitacoes": "palpitações",
    "inchaco nas pernas": "inchaço nas pernas", "pressao alta": "pressão alta",
    "visao turva": "visão turva", "visao embacada": "visão embaçada", "visao dupla": "visão dupla",
    "sensibilidade a luz": "sensibilidade à luz", "diarreia": "diarreia", "nausea": "náusea",
    "ardencia nos olhos": "ardência nos olhos", "cansaco": "cansaço", "coracao": "coração",
    "visao": "visão", "colirio": "colírio", "palpebra": "pálpebra", "paralisia": "paralisia",
    "ausencia": "ausência", "hemorragia": "hemorragia", "erupcao": "erupção",
}

_NEGADORES = frozenset({"sem", "nao", "nunca", "nega", "negou", "ausencia"})
_JANELA_NEGACAO = 3  # palavras antes do termo em que um negador anula o termo


@dataclass(frozen=True)
class ResultadoClassificacao:
    urgencia: str
    especialidade: str
    justificativa: str
    termos_urgencia: Tuple[str, ...] = ()
    termos_especialidade: Tuple[str, ...] = ()


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos nem pontuação, com espaços simples."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acento).split())


def _ocorrencias(texto: str, termos: Tuple[str, ...]) -> List[Tuple[int, int, str]]:
    """(início, fim, termo) de cada termo encontrado, sem os negados e sem os contidos
    em um termo mais longo (ex.: 'dor no peito' dentro de 'dor forte no peito')."""
    achados = []
    for termo in termos:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])", texto):
            antes = texto[: m.start()].split()[-_JANELA_NEGACAO:]
            if _NEGADORES.intersection(antes):
                continue
            achados.append((m.start(), m.end(), termo))
    achados.sort(key=lambda a: (a[0], -(a[1] - a[0])))
    finais: List[Tuple[int, int, str]] = []
    for ini, fim, termo in achados:
        if any(i <= ini and fim <= f and (i, f) != (ini, fim) for i, f, _ in achados):
            continue
        if (ini, fim, termo) not in finais:
            finais.append((ini, fim, termo))
    return finais


def _unicos_na_ordem(achados: List[Tuple[int, int, str]]) -> Tuple[str, ...]:
    vistos: List[str] = []
    for _, _, termo in sorted(achados):
        if termo not in vistos:
            vistos.append(termo)
    return tuple(vistos)


def encontrar_termos(texto: str, termos: Tuple[str, ...]) -> Tuple[str, ...]:
    """Termos (aceita acento) presentes no relato, na ordem em que aparecem.

    Ignora caixa, acentos e pontuação, termos negados ("sem", "não"...) e termos
    contidos em outro mais longo. Os termos voltam normalizados (sem acento).
    """
    return _unicos_na_ordem(_ocorrencias(normalizar(texto), tuple(normalizar(t) for t in termos)))


def classificar_texto(texto: str) -> ResultadoClassificacao:
    """Classifica o relato livre. Vence o nível de urgência mais alto encontrado."""
    t = normalizar(texto)

    urgencia, termos_u = URGENCIA_PADRAO, ()
    for nivel in ("emergencia", "alta", "media"):
        achados = _ocorrencias(t, TERMOS_URGENCIA[nivel])
        if achados:
            urgencia, termos_u = nivel, _unicos_na_ordem(achados)
            break

    especialidade, termos_e, melhor = ESPECIALIDADE_PADRAO, (), 0
    for nome, termos in TERMOS_ESPECIALIDADE.items():  # empate: vence a primeira da lista
        achados = _ocorrencias(t, termos)
        if len(achados) > melhor:
            especialidade, termos_e, melhor = nome, _unicos_na_ordem(achados), len(achados)

    if termos_u:
        justificativa = "Classificado como %s por mencionar: %s" % (
            ROTULO_NIVEL[urgencia], ", ".join(EXIBICAO.get(x, x) for x in termos_u))
    else:
        justificativa = "Nenhum termo de urgência identificado; classificado como baixa"
    if termos_e:
        justificativa += ". Especialidade sugerida: %s (termos: %s)" % (
            ROTULO_ESPECIALIDADE[especialidade], ", ".join(EXIBICAO.get(x, x) for x in termos_e))
    else:
        justificativa += ". Especialidade sugerida: clínica geral (padrão)"
    return ResultadoClassificacao(urgencia, especialidade, justificativa, termos_u, termos_e)
