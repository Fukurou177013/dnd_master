from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

EMBEDDING_DIMENSIONS = 1024


class Settings(BaseSettings):
    database_url: str
    cookie_secure: bool = False
    session_ttl_days: int = 30
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: str = ""

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_chat_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"
    llm_embedding_dimensions: int = EMBEDDING_DIMENSIONS
    llm_timeout_seconds: float = 30.0
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


settings = Settings()
