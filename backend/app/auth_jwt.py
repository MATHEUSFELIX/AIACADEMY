"""Validate Supabase-issued JWTs.

Supports:
- Legacy symmetric: HS256 with SUPABASE_JWT_SECRET (dashboard » JWT Settings » JWT Secret).
- Current asymmetric: ES256 / RS256 via JWKS at ``{SUPABASE_URL}/auth/v1/.well-known/jwks.json``.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import InvalidAudienceError, PyJWKClient

from app.config import get_settings

logger = logging.getLogger(__name__)

_ASYMMETRIC_ALGS = frozenset({"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"})


@dataclass
class JwtPayload:
    sub: uuid.UUID
    email: str


@lru_cache(maxsize=8)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url)


def _payload_to_model(payload: dict) -> JwtPayload:
    sub = uuid.UUID(str(payload["sub"]))
    meta = payload.get("user_metadata") or {}
    email = str(payload.get("email") or meta.get("email") or "")
    return JwtPayload(sub=sub, email=email)


def _decode_with_audience_optional(token: str, key: Any, algorithms: list[str]) -> dict:
    try:
        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except InvalidAudienceError:
        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            options={"verify_aud": False, "require": ["exp", "sub"]},
        )


def decode_supabase_jwt(token: str) -> JwtPayload:
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError as e:
        raise ValueError("Malformed JWT header") from e

    alg = (header.get("alg") or "HS256").upper()

    # ── Symmetric (projeto antigo ou segredo fixo ainda em uso)
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            logger.error("SUPABASE_JWT_SECRET is not configured (required for HS256 tokens)")
            raise ValueError("JWT verification not configured")
        payload = _decode_with_audience_optional(
            token,
            settings.supabase_jwt_secret,
            ["HS256"],
        )
        return _payload_to_model(payload)

    # ── Assimétrico via JWKS (JWT Signing Keys no Supabase atual)
    if alg not in _ASYMMETRIC_ALGS:
        logger.warning("Unexpected JWT alg=%s", alg)

    base = (settings.supabase_url or "").rstrip("/")
    if not base:
        logger.error(
            "SUPABASE_URL is not configured — required to verify asymmetric Supabase JWTs (%s)",
            alg,
        )
        raise ValueError("SUPABASE_URL not configured for JWKS verification")

    jwks_url = f"{base}/auth/v1/.well-known/jwks.json"
    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
    except jwt.exceptions.PyJWTError as e:
        logger.warning("JWKS signing key lookup failed: %s", e)
        raise ValueError("JWKS verification failed") from e

    payload = _decode_with_audience_optional(token, signing_key.key, [alg])
    logger.debug("Verified Supabase JWT via JWKS (%s)", alg)
    return _payload_to_model(payload)
