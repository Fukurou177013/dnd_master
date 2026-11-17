import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 20", name="ck_characters_level_range"),
        CheckConstraint(
            "strength BETWEEN 1 AND 30 AND "
            "dexterity BETWEEN 1 AND 30 AND "
            "constitution BETWEEN 1 AND 30 AND "
            "intelligence BETWEEN 1 AND 30 AND "
            "wisdom BETWEEN 1 AND 30 AND "
            "charisma BETWEEN 1 AND 30",
            name="ck_characters_ability_range",
        ),
        CheckConstraint("max_hp >= 0", name="ck_characters_max_hp_non_negative"),
        CheckConstraint("current_hp >= 0", name="ck_characters_current_hp_non_negative"),
        CheckConstraint("armor_class >= 0", name="ck_characters_armor_class_non_negative"),
        CheckConstraint("speed >= 0", name="ck_characters_speed_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    level: Mapped[int] = mapped_column(SmallInteger)
    species: Mapped[str] = mapped_column(String(50))
    character_class: Mapped[str] = mapped_column(String(50))
    background: Mapped[str] = mapped_column(String(50))
    strength: Mapped[int] = mapped_column(SmallInteger)
    dexterity: Mapped[int] = mapped_column(SmallInteger)
    constitution: Mapped[int] = mapped_column(SmallInteger)
    intelligence: Mapped[int] = mapped_column(SmallInteger)
    wisdom: Mapped[int] = mapped_column(SmallInteger)
    charisma: Mapped[int] = mapped_column(SmallInteger)
    max_hp: Mapped[int] = mapped_column(Integer)
    current_hp: Mapped[int] = mapped_column(Integer)
    armor_class: Mapped[int] = mapped_column(Integer)
    speed: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
