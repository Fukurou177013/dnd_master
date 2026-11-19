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


def test_default_llm_url_is_local_ollama() -> None:
    settings = build_settings()
    assert settings.llm_base_url == "http://localhost:11434/v1"


@pytest.mark.parametrize(
    "url",
    [
        "https://opencode.ai/zen/go",
        "https://opencode.ai/zen/go/v1",
        "https://opencode.ai/inference/go",
        "https://opencode.ai/inference/go/v1",
    ],
)
def test_opencode_go_endpoint_is_rejected(url: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_settings(llm_base_url=url)
    assert "OpenCode Go" in str(excinfo.value)


@pytest.mark.parametrize(
    "url",
    [
        "https://opencode.ai./zen/go/v1",
        "https://opencode.ai/zen/%67o/v1",
        "https://opencode.ai/inference/%67o/v1",
    ],
)
def test_opencode_go_guard_normalizes_host_and_path(url: str) -> None:
    with pytest.raises(ValidationError, match="OpenCode Go"):
        build_settings(llm_base_url=url)


def test_opencode_pay_as_you_go_endpoint_is_allowed() -> None:
    settings = build_settings(
        llm_base_url="https://opencode.ai/inference/openai/v1"
    )
    assert settings.llm_base_url.endswith("/openai/v1")


def test_local_ollama_endpoint_is_allowed() -> None:
    settings = build_settings(llm_base_url="http://localhost:11434/v1")
    assert settings.llm_base_url == "http://localhost:11434/v1"
