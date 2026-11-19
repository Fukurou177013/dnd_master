import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings

PREMISE_MAX_LENGTH = 500


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    character_id: uuid.UUID
    premise: str | None = Field(default=None, max_length=PREMISE_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Название не может быть пустым")
        return stripped

    @field_validator("premise")
    @classmethod
    def strip_premise(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CampaignSummary(BaseModel):
    facts: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    npcs: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)


class CampaignPublic(BaseModel):
    id: uuid.UUID
    name: str
    character_id: uuid.UUID
    premise: str | None
    summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=settings.max_message_length)
    client_message_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Сообщение не может быть пустым")
        return stripped


class CampaignMessagePublic(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sequence: int
    roll: dict[str, Any] | None
    sources: list[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignExchange(BaseModel):
    user_message: CampaignMessagePublic
    assistant_message: CampaignMessagePublic
    memory_update_scheduled: bool
