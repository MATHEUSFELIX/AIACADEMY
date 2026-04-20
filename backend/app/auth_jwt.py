"""Validate Supabase-issued JWTs (HS256 with project JWT secret)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

import jwt
from jwt import InvalidAudienceError

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class JwtPayload:
    sub: uuid.UUID
    email: str


def decode_supabase_jwt(token: str) -> JwtPayload:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        logger.error("SUPABASE_JWT_SECRET is not configured")
        raise ValueError("JWT verification not configured")

    key = settings.supabase_jwt_secret
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except InvalidAudienceError:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            options={"verify_aud": False, "require": ["exp", "sub"]},
        )

    sub = uuid.UUID(str(payload["sub"]))
    meta = payload.get("user_metadata") or {}
    email = str(payload.get("email") or meta.get("email") or "")
    return JwtPayload(sub=sub, email=email)
