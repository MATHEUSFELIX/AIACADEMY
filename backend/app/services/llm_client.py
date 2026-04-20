"""Provedor LLM configurável: Ollama Cloud (padrão) ou Anthropic Claude."""

from __future__ import annotations

import logging

import httpx
from anthropic import Anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)


def _normalize_provider(raw: str) -> str:
    p = (raw or "ollama_cloud").strip().lower()
    if p in ("ollama", "ollama_cloud", "ollama-cloud"):
        return "ollama_cloud"
    if p in ("anthropic", "claude"):
        return "anthropic"
    return p


def llm_complete(system: str, user: str, max_tokens: int) -> str:
    """
    Gera texto do assistente. Ordem de prioridade por `LLM_PROVIDER`:
    - ollama_cloud (default): `OLLAMA_HOST` + `OLLAMA_API_KEY` + `/api/chat`
    - anthropic: `ANTHROPIC_API_KEY` + Messages API
    """
    settings = get_settings()
    provider = _normalize_provider(settings.llm_provider)

    if provider == "anthropic":
        return _complete_anthropic(system, user, max_tokens)

    if provider != "ollama_cloud":
        logger.warning("LLM_PROVIDER desconhecido %r — usando ollama_cloud", settings.llm_provider)

    return _complete_ollama_cloud(system, user, max_tokens)


def _complete_anthropic(system: str, user: str, max_tokens: int) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return (
            "[Anthropic não configurado — defina ANTHROPIC_API_KEY ou use LLM_PROVIDER=ollama_cloud]\n\n"
            f"System: {system[:200]}…\nUser: {user[:200]}…"
        )
    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    block = msg.content[0]
    if block.type != "text":
        return ""
    return block.text


def _complete_ollama_cloud(system: str, user: str, max_tokens: int) -> str:
    settings = get_settings()
    host = settings.ollama_host.rstrip("/")
    api_key = settings.ollama_api_key
    model = settings.ollama_model

    if not api_key:
        return (
            "[Ollama Cloud — defina OLLAMA_API_KEY em https://ollama.com/settings/keys]\n\n"
            f"System: {system[:200]}…\nUser: {user[:200]}…"
        )

    url = f"{host}/api/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        logger.error("Ollama HTTP error: %s %s", e.response.status_code, e.response.text[:500])
        return f"[Erro Ollama Cloud HTTP {e.response.status_code}] {e.response.text[:400]}"
    except Exception as e:
        logger.exception("Ollama request failed")
        return f"[Erro ao chamar Ollama Cloud: {e!s}]"

    msg = data.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    return str(content or data.get("response", ""))
