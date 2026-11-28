import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AbilityScoreMethod = Literal["manual", "standard_array", "point_buy", "roll_4d6"]

REQUIRED_UPDATE_FIELDS = {
    "name",
    "level",
    "species",
    "character_class",
    "background",
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
    "max_hp",
    "current_hp",
    "armor_class",
    "speed",
    "data",
    "ability_score_method",
    "background_ability_bonus",
}


class CharacterBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=1, le=20)
    species: str = Field(min_length=1, max_length=50)
    character_class: str = Field(min_length=1, max_length=50)
    background: str = Field(min_length=1, max_length=50)
    strength: int = Field(ge=1, le=30)
    dexterity: int = Field(ge=1, le=30)
    constitution: int = Field(ge=1, le=30)
    intelligence: int = Field(ge=1, le=30)
    wisdom: int = Field(ge=1, le=30)
    charisma: int = Field(ge=1, le=30)
    max_hp: int = Field(ge=0)
    current_hp: int = Field(ge=0)
    armor_class: int = Field(ge=0)
    speed: int = Field(ge=0)
    notes: str | None = Field(default=None, max_length=10000)
    data: dict[str, Any] = Field(default_factory=dict)


class CharacterCreate(CharacterBase):
    ability_score_method: AbilityScoreMethod
    background_ability_bonus: dict[str, int]
    max_hp: int | None = Field(default=None, ge=0)
    current_hp: int | None = Field(default=None, ge=0)
    armor_class: int | None = Field(default=None, ge=0)
    speed: int | None = Field(default=None, ge=0)


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    level: int | None = Field(default=None, ge=1, le=20)
    species: str | None = Field(default=None, min_length=1, max_length=50)
    character_class: str | None = Field(default=None, min_length=1, max_length=50)
    background: str | None = Field(default=None, min_length=1, max_length=50)
    ability_score_method: AbilityScoreMethod | None = None
    background_ability_bonus: dict[str, int] | None = None
    strength: int | None = Field(default=None, ge=1, le=30)
    dexterity: int | None = Field(default=None, ge=1, le=30)
    constitution: int | None = Field(default=None, ge=1, le=30)
    intelligence: int | None = Field(default=None, ge=1, le=30)
    wisdom: int | None = Field(default=None, ge=1, le=30)
    charisma: int | None = Field(default=None, ge=1, le=30)
    max_hp: int | None = Field(default=None, ge=0)
    current_hp: int | None = Field(default=None, ge=0)
    armor_class: int | None = Field(default=None, ge=0)
    speed: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=10000)
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> CharacterUpdate:
        for field in self.model_fields_set & REQUIRED_UPDATE_FIELDS:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть null")
        return self


class CharacterPublic(CharacterBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AbilityScoreRoll(BaseModel):
    method: AbilityScoreMethod
    scores: dict[str, int]
