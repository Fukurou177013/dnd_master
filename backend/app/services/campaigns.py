from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, CampaignMemory, CampaignMessage, Character
from app.models.campaign import EMPTY_SUMMARY
from app.schemas.campaign import CampaignCreate


class CharacterNotOwnedError(Exception):
    pass


async def list_campaigns(db: AsyncSession, user_id: uuid.UUID) -> list[Campaign]:
    result = await db.scalars(
        select(Campaign)
        .where(Campaign.user_id == user_id)
        .order_by(Campaign.created_at.desc())
    )
    return list(result)


async def get_campaign(
    db: AsyncSession,
    user_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> Campaign | None:
    return await db.scalar(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
    )


async def create_campaign(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: CampaignCreate,
) -> Campaign:
    character_id = await db.scalar(
        select(Character.id).where(
            Character.id == payload.character_id,
            Character.user_id == user_id,
        )
    )
    if character_id is None:
        raise CharacterNotOwnedError

    campaign = Campaign(
        user_id=user_id,
        character_id=character_id,
        name=payload.name,
        memory=CampaignMemory(summary=copy.deepcopy(EMPTY_SUMMARY)),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(
    db: AsyncSession,
    user_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> bool:
    campaign = await get_campaign(db, user_id, campaign_id)
    if campaign is None:
        return False
    await db.delete(campaign)
    await db.commit()
    return True


async def list_messages(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    *,
    limit: int = 100,
) -> list[CampaignMessage]:
    message_ids = (
        select(CampaignMessage.id)
        .where(CampaignMessage.campaign_id == campaign_id)
        .order_by(CampaignMessage.sequence.desc())
        .limit(limit)
        .subquery()
    )
    result = await db.scalars(
        select(CampaignMessage)
        .where(CampaignMessage.id.in_(select(message_ids.c.id)))
        .order_by(CampaignMessage.sequence.asc())
    )
    return list(result)


async def get_message_by_client_id(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    client_message_id: str,
) -> CampaignMessage | None:
    return await db.scalar(
        select(CampaignMessage).where(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.client_message_id == client_message_id,
        )
    )


async def get_assistant_reply(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    user_message_id: uuid.UUID,
) -> CampaignMessage | None:
    return await db.scalar(
        select(CampaignMessage).where(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.role == "assistant",
            CampaignMessage.message_metadata["reply_to"].astext
            == str(user_message_id),
        )
    )


async def next_sequence(db: AsyncSession, campaign_id: uuid.UUID) -> int:
    current = await db.scalar(
        select(func.max(CampaignMessage.sequence)).where(
            CampaignMessage.campaign_id == campaign_id
        )
    )
    return (current or 0) + 1


async def add_message(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    role: str,
    content: str,
    metadata: dict[str, Any],
    client_message_id: str | None = None,
) -> CampaignMessage:
    message = CampaignMessage(
        campaign_id=campaign_id,
        role=role,
        content=content,
        sequence=await next_sequence(db, campaign_id),
        client_message_id=client_message_id,
        message_metadata=metadata,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def update_memory(
    db: AsyncSession,
    campaign: Campaign,
    summary: dict[str, Any],
) -> None:
    if campaign.memory is None:
        campaign.memory = CampaignMemory(summary=summary)
    else:
        campaign.memory.summary = summary
    await db.commit()
