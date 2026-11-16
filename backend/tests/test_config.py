import pytest
from pydantic import ValidationError

from app.core.config import EMBEDDING_DIMENSIONS, Settings

BASE_SETTINGS = {
    "database_url": "postgresql+psycopg://dnd:dnd@localhost:5433/dnd",
}


def build_settings(**overrides: object) -> Settings:
    return Settings(**{**BASE_SETTINGS, **overrides})


def test_samesite_none_requires_secure_cookie() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_settings(session_cookie_samesite="none", cookie_secure=False)
    assert "COOKIE_SECURE" in str(excinfo.value)


def test_samesite_none_with_secure_cookie_is_allowed() -> None:
    settings = build_settings(session_cookie_samesite="none", cookie_secure=True)
    assert settings.session_cookie_samesite == "none"


def test_default_cookie_settings_are_allowed() -> None:
    settings = build_settings()
    assert settings.session_cookie_samesite == "lax"
    assert settings.cookie_secure is False


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_settings(cors_origins="*")
    assert "wildcard" in str(excinfo.value)

    with pytest.raises(ValidationError):
        build_settings(
            cors_origins="http://localhost:5173,https://*.example.com"
        )


def test_explicit_cors_origins_are_allowed() -> None:
    settings = build_settings(
        cors_origins="http://localhost:5173, https://app.example.com"
    )
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://app.example.com",
    ]


def test_embedding_dimensions_must_match_schema() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_settings(llm_embedding_dimensions=EMBEDDING_DIMENSIONS + 1)
    assert "srd_chunks.embedding" in str(excinfo.value)

    settings = build_settings(llm_embedding_dimensions=EMBEDDING_DIMENSIONS)
    assert settings.llm_embedding_dimensions == EMBEDDING_DIMENSIONS
