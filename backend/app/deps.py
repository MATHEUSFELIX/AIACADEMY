"""FastAPI dependencies — database session and current student."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from app.auth_jwt import decode_supabase_jwt
from app.config import get_settings
from app.db import get_db
from app.models import Student
from app.services.student_service import ensure_student

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def get_current_student(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Student:
    settings = get_settings()

    if settings.dev_skip_auth:
        sid = settings.dev_student_id or "00000000-0000-0000-0000-000000000001"
        auth_uid = uuid.UUID(sid)
        email = "dev@masterai.local"
        return ensure_student(db, auth_user_id=auth_uid, email=email, default_name="Dev User")

    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        payload = decode_supabase_jwt(creds.credentials)
    except ExpiredSignatureError as e:
        logger.info("JWT expired: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except (InvalidTokenError, ValueError, KeyError) as e:
        logger.warning("JWT invalid: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    email = payload.email or "user@unknown.local"
    default_name = email.split("@")[0][:150]
    return ensure_student(
        db,
        auth_user_id=payload.sub,
        email=email,
        default_name=default_name,
    )
