"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import auth as auth_router
from app.routers import brainagent as brainagent_router
from app.routers import diagnostic as diagnostic_router
from app.routers import health as health_router
from app.routers import kb as kb_router
from app.routers import lessons as lessons_router
from app.routers import progress as progress_router
from app.routers import students as students_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def _cors_origins() -> list[str]:
    extra = [o.strip() for o in (settings.cors_allow_origins or "").split(",") if o.strip()]
    if settings.environment == "development":
        return ["http://localhost:3000", "http://127.0.0.1:3000", *extra]
    return ["https://masterai.academy", *extra]


app = FastAPI(title="MasterAI Academy API", version="1.0.0")

_cors_kw: dict = {
    "allow_origins": _cors_origins(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
# Qualquer porta em localhost / 127.0.0.1 / ::1 (útil se NEXT_PUBLIC_API_URL apontar direto para :8000)
if settings.environment == "development":
    _cors_kw["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"

app.add_middleware(CORSMiddleware, **_cors_kw)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": str(exc),
            "error_code": "VALIDATION_ERROR",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )


app.include_router(health_router.router, tags=["health"])
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(students_router.router, tags=["students"])
app.include_router(diagnostic_router.router, prefix="/diagnostic", tags=["diagnostic"])
app.include_router(lessons_router.router, tags=["lessons"])
app.include_router(progress_router.router, prefix="/progress", tags=["progress"])
app.include_router(brainagent_router.router, prefix="/brainagent", tags=["brainagent"])
app.include_router(kb_router.router, prefix="/kb", tags=["kb"])
