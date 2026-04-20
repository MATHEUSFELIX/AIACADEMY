"""Provedor LLM configurável: Ollama (oficial ollama-python) ou Anthropic Claude.

Ollama Cloud segue https://github.com/ollama/ollama-python (Client + host + Bearer).
"""

from __future__ import annotations

import logging

import httpx
from anthropic import Anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)

# Na Ollama Cloud, num_predict muito baixo pode devolver message.content vazio (modelos com "thinking").
OLLAMA_MIN_NUM_PREDICT = 128


def _ollama_predict_cap(max_tokens: int) -> int:
    return max(max_tokens, OLLAMA_MIN_NUM_PREDICT)


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
    - ollama_cloud (default): biblioteca `ollama` → `POST /api/chat` (igual ao repo ollama-python)
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


def _ollama_auth_help() -> str:
    return (
        "Verifique OLLAMA_API_KEY no .env (sem aspas extras) — crie em "
        "https://ollama.com/settings/keys — e reinicie o backend. "
        "Alternativa: LLM_PROVIDER=anthropic com ANTHROPIC_API_KEY; ou Ollama local "
        "(OLLAMA_HOST=http://host.docker.internal:11434 e OLLAMA_API_KEY vazio)."
    )


def _ollama_host_is_local(host: str) -> bool:
    """Ollama em máquina local (Docker Desktop → host) não exige Bearer."""
    h = (host or "").lower().rstrip("/")
    return bool(
        h
        and (
            "localhost" in h
            or "127.0.0.1" in h
            or "host.docker.internal" in h
            or ":11434" in h
            or h.endswith(":11434")
        )
    )


def _complete_ollama_local_httpx(
    host: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
) -> str:
    """Ollama local sem API key — httpx direto (evita injeção automática de Bearer do Client)."""
    url = f"{host.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json"}
    body: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": _ollama_predict_cap(max_tokens)},
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        logger.error("Ollama local HTTP error: %s %s", e.response.status_code, e.response.text[:500])
        return f"[Erro Ollama local HTTP {e.response.status_code}] {e.response.text[:400]}"
    except Exception as e:
        logger.exception("Ollama local request failed")
        return f"[Erro ao chamar Ollama local: {e!s}]"

    msg = data.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    return str(content or data.get("response", ""))


def _complete_ollama_client(
    host: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
) -> str:
    """Cloud (ou host remoto com chave): mesmo fluxo que o README do ollama-python."""
    from ollama import Client
    from ollama import ResponseError

    try:
        client = Client(
            host=host,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )
        resp = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=False,
            options={"num_predict": _ollama_predict_cap(max_tokens)},
        )
    except ResponseError as e:
        code = e.status_code
        snippet = str(e.error)[:400]
        logger.error("Ollama ResponseError: %s %s", code, snippet)
        if code in (401, 403):
            return (
                f"[Ollama Cloud: acesso negado ({code}). {_ollama_auth_help()}]\n\n"
                f"Resposta: {snippet}"
            )
        return f"[Erro Ollama HTTP {code}] {snippet}"
    except Exception as e:
        logger.exception("Ollama client.chat failed")
        return f"[Erro ao chamar Ollama: {e!s}]"

    content = resp.message.content if resp.message else None
    if isinstance(content, str):
        return content
    return str(content or "")


def _complete_ollama_cloud(system: str, user: str, max_tokens: int) -> str:
    settings = get_settings()
    host = settings.ollama_host.rstrip("/")
    api_key = (settings.ollama_api_key or "").strip()
    model = (settings.ollama_model or "").strip() or "gpt-oss:120b"
    local_no_auth = _ollama_host_is_local(host) and not api_key

    if not api_key and not local_no_auth:
        return (
            "[Ollama — defina OLLAMA_API_KEY (cloud: https://ollama.com/settings/keys) "
            "ou use Ollama local: OLLAMA_HOST=http://host.docker.internal:11434 sem chave]\n\n"
            f"System: {system[:200]}…\nUser: {user[:200]}…"
        )

    if local_no_auth:
        return _complete_ollama_local_httpx(host, model, system, user, max_tokens)

    return _complete_ollama_client(host, api_key, model, system, user, max_tokens)
