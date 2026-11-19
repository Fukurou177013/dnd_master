import re
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

EMBEDDING_DIMENSIONS = 1024

_OPENCODE_HOSTS = {"opencode.ai", "www.opencode.ai"}
_OPENCODE_GO_PATH = re.compile(r"/(?:zen|inference)/go(?:/|$)")


class Settings(BaseSettings):
    database_url: str
    cookie_secure: bool = False
    session_ttl_days: int = 30
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: str = ""

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_chat_model: str = "qwen3:14b"
    llm_embedding_model: str = "qwen3-embedding-cpu"
    llm_embedding_dimensions: int = EMBEDDING_DIMENSIONS
    llm_timeout_seconds: float = 120.0
    llm_max_output_tokens: int = 700
    llm_temperature: float = 0.7
    llm_system_suffix: str = ""

    retrieval_top_k: int = 4
    recent_message_limit: int = 12
    max_message_length: int = 4000
    chat_rate_limit_per_minute: int = 30

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_deploy_safety(self) -> Settings:
        self._reject_opencode_go()

        if self.session_cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "SESSION_COOKIE_SAMESITE=none требует COOKIE_SECURE=true: "
                "браузеры отклоняют SameSite=None cookie без Secure, "
                "и авторизация перестанет работать"
            )

        for origin in self.cors_origin_list:
            if "*" in origin:
                raise ValueError(
                    f"CORS_ORIGINS не может содержать wildcard ({origin}): "
                    "API использует cookie-сессии, поэтому credentialed-CORS "
                    "допустим только для явно перечисленных origin"
                )

        if self.llm_embedding_dimensions != EMBEDDING_DIMENSIONS:
            raise ValueError(
                "LLM_EMBEDDING_DIMENSIONS="
                f"{self.llm_embedding_dimensions} не совпадает со схемой "
                f"srd_chunks.embedding ({EMBEDDING_DIMENSIONS}). Для другой "
                "размерности обновите EMBEDDING_DIMENSIONS, создайте миграцию "
                "и заново импортируйте SRD-корпус"
            )

        return self

    def _reject_opencode_go(self) -> None:
        parsed = urlsplit(self.llm_base_url.strip())
        host = (parsed.hostname or "").rstrip(".").casefold()
        if host not in _OPENCODE_HOSTS and not host.endswith(".opencode.ai"):
            return
        path = unquote(parsed.path).casefold()
        if _OPENCODE_GO_PATH.search(path):
            raise ValueError(
                "LLM_BASE_URL указывает на OpenCode Go. Подписка Go разрешена "
                "только для coding-агента, а трафик приложения к ней направлять "
                "нельзя. Используйте локальную Ollama или другого провайдера "
                "(см. OPENCODE_GO_POLICY.md)"
            )


settings = Settings()
