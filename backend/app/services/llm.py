from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import settings

_http_client: httpx.AsyncClient | None = None
logger = logging.getLogger(__name__)


def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.llm_base_url.rstrip("/"),
        timeout=settings.llm_timeout_seconds,
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
    )


def set_http_client(client: httpx.AsyncClient | None) -> None:
    global _http_client
    _http_client = client


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise ProviderUnavailableError("HTTP-клиент LLM не инициализирован")
    return _http_client


class ProviderError(Exception):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class ChatProvider(Protocol):
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
    ) -> str: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIChatProvider:
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not settings.llm_api_key:
            raise ProviderUnavailableError("LLM-провайдер не настроен")

        payload = {
            "model": settings.llm_chat_model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await get_http_client().post(
                "/chat/completions", json=payload
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Превышено время ожидания LLM") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("LLM-провайдер недоступен") from exc

        if response.status_code >= 400:
            raise ProviderUnavailableError(
                f"LLM-провайдер вернул ошибку {response.status_code}"
            )

        try:
            payload_data = response.json()
            choice = payload_data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderUnavailableError(
                "LLM-провайдер вернул неожиданный ответ"
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderUnavailableError("LLM-провайдер вернул пустой ответ")

        finish_reason = choice.get("finish_reason")
        usage = payload_data.get("usage")
        completion_tokens = (
            usage.get("completion_tokens") if isinstance(usage, dict) else None
        )
        logger.info(
            "LLM completion metadata: finish_reason=%s completion_tokens=%s "
            "content_chars=%d",
            finish_reason,
            completion_tokens,
            len(content),
        )
        if finish_reason == "length":
            logger.warning(
                "LLM completion reached token limit: completion_tokens=%s "
                "content_chars=%d",
                completion_tokens,
                len(content),
            )
        return content.strip()


class OpenAIEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.llm_api_key:
            raise ProviderUnavailableError("Embedding-провайдер не настроен")
        if not texts:
            return []

        payload = {
            "model": settings.llm_embedding_model,
            "input": texts,
            "dimensions": settings.llm_embedding_dimensions,
        }

        try:
            response = await get_http_client().post("/embeddings", json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Превышено время ожидания embeddings") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Embedding-провайдер недоступен") from exc

        if response.status_code >= 400:
            raise ProviderUnavailableError(
                f"Embedding-провайдер вернул ошибку {response.status_code}"
            )

        try:
            rows: list[dict[str, Any]] = response.json()["data"]
            rows.sort(key=lambda row: row["index"])
            vectors = [row["embedding"] for row in rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderUnavailableError(
                "Embedding-провайдер вернул неожиданный ответ"
            ) from exc

        if len(vectors) != len(texts):
            raise ProviderUnavailableError(
                "Embedding-провайдер вернул неверное число векторов"
            )
        for vector in vectors:
            if len(vector) != settings.llm_embedding_dimensions:
                raise ProviderUnavailableError(
                    "Размерность embeddings не совпадает с настройками"
                )
        return vectors


_chat_provider = OpenAIChatProvider()
_embedding_provider = OpenAIEmbeddingProvider()


def get_chat_provider() -> ChatProvider:
    return _chat_provider


def get_embedding_provider() -> EmbeddingProvider:
    return _embedding_provider
