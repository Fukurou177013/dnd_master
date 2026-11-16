from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import EMBEDDING_DIMENSIONS
from app.db.base import Base

EMPTY_SUMMARY: dict[str, list[str]] = {
    "facts": [],
    "goals": [],
    "npcs": [],
    "locations": [],
    "open_threads": [],
}


class Campaign(Base):
    __tablename__ = "campaigns"

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
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memory: Mapped[CampaignMemory | None] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    @property
    def summary(self) -> dict[str, Any]:
        if self.memory is None:
            return dict(EMPTY_SUMMARY)
        return self.memory.summary


class CampaignMemory(Base):
    __tablename__ = "campaign_memories"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("""'{"facts": [], "goals": [], "npcs": [], "locations": [], "open_threads": []}'::jsonb"""),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped[Campaign] = relationship(back_populates="memory")


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_campaign_messages_role"),
        CheckConstraint("sequence > 0", name="ck_campaign_messages_sequence_positive"),
        UniqueConstraint(
            "campaign_id",
            "sequence",
            name="uq_campaign_messages_campaign_sequence",
        ),
        UniqueConstraint(
            "campaign_id",
            "client_message_id",
            name="uq_campaign_messages_campaign_client_message",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer)
    client_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def roll(self) -> dict[str, Any] | None:
        if self.role != "assistant":
            return None
        roll = self.message_metadata.get("roll")
        return roll if isinstance(roll, dict) else None

    @property
    def sources(self) -> list[dict[str, Any]]:
        sources = self.message_metadata.get("sources")
        return sources if isinstance(sources, list) else []


class SrdChunk(Base):
    __tablename__ = "srd_chunks"
    __table_args__ = (
        Index(
            "ix_srd_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    chunk_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(200))
    section: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    license: Mapped[str] = mapped_column(String(50))
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
