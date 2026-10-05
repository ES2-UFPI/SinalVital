import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

MODO_IA = os.getenv("MODO_IA", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _classificar_mock(texto: str) -> dict:
    """Simulação local por palavras-chave: não chama nenhuma API, não gera custo."""
    t = texto.lower()
    if "dor no peito" in t or "falta de ar" in t:
        urgencia = "emergencia"
    elif "febre" in t or "dor forte" in t:
        urgencia = "alta"
    else:
        urgencia = "baixa"

    if "peito" in t or "coração" in t:
        especialidade = "cardiologia"
    elif "pele" in t or "mancha" in t:
        especialidade = "dermatologia"
    else:
        especialidade = "clinica_geral"

    return {"urgencia": urgencia, "especialidade_sugerida": especialidade}


def _classificar_real(texto: str) -> dict:
    """Chama a API da Anthropic (Claude). Gasta créditos da conta."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada no .env")

    prompt = (
        "Responda APENAS com um JSON válido, sem texto antes ou depois, no formato:\n"
        '{"urgencia": "baixa|media|alta|emergencia", "especialidade_sugerida": "..."}\n\n'
        f"Sintomas: {texto}"
    )
    resposta = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30.0,
    )
    resposta.raise_for_status()
    blocos = resposta.json().get("content", [])
    texto_resposta = "".join(b.get("text", "") for b in blocos if b.get("type") == "text")
    limpo = texto_resposta.replace("```json", "").replace("```", "").strip()
    return json.loads(limpo)


def classificar_sintomas(texto: str) -> dict:
    """Ponto de entrada único: escolhe mock ou real conforme MODO_IA."""
    if MODO_IA == "real":
        return _classificar_real(texto)
    return _classificar_mock(texto)
