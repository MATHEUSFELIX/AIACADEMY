"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    # Domínios extras permitidos no CORS (separados por vírgula), ex.: https://xxx.vercel.app
    cors_allow_origins: str = ""
    secret_key: str = "change-me"

    database_url: str = "postgresql://masterai:masterai_dev_2026@localhost:5432/masterai_academy"

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""  # JWT secret from Supabase Dashboard (legacy HS256)

    # LLM: padrão Ollama Cloud; use LLM_PROVIDER=anthropic para Claude
    llm_provider: str = "ollama_cloud"  # ollama_cloud | anthropic
    ollama_host: str = "https://ollama.com"
    ollama_api_key: str = ""  # OLLAMA_API_KEY — chave em ollama.com/settings/keys
    ollama_model: str = "gpt-oss:120b"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    chromadb_host: str = "localhost"
    chromadb_port: int = 8001
    chromadb_token: str = ""

    redis_url: str = "redis://:masterai_redis_2026@localhost:6379/0"

    brainagent_rate_limit_per_hour: int = 20
    brainagent_max_tokens_evaluation: int = 1500
    brainagent_max_tokens_chat: int = 800
    brainagent_max_tokens_recommendation: int = 500
    brainagent_cache_ttl: int = 3600

    dev_skip_auth: bool = False
    dev_student_id: str | None = None

    @field_validator(
        "ollama_api_key",
        "anthropic_api_key",
        "supabase_jwt_secret",
        "supabase_service_key",
        mode="before",
    )
    @classmethod
    def strip_optional_secrets(cls, v: object) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
            s = s[1:-1].strip()
        return s

    @field_validator("ollama_host", mode="before")
    @classmethod
    def normalize_ollama_host(cls, v: object) -> str:
        """Base URL apenas (ex.: https://ollama.com). Se vier …/api, remove — senão /api/chat vira …/api/api/chat."""
        if v is None or str(v).strip() == "":
            return "https://ollama.com"
        h = str(v).strip().rstrip("/")
        while h.lower().endswith("/api"):
            h = h[:-4].rstrip("/")
        return h or "https://ollama.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
