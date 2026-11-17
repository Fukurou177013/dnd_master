import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Character
from app.rules.character_options import build_character_values
from app.schemas.character import CharacterCreate, CharacterUpdate


async def list_characters(db: AsyncSession, user_id: uuid.UUID) -> list[Character]:
    result = await db.scalars(
        select(Character)
        .where(Character.user_id == user_id)
        .order_by(Character.created_at.desc())
    )
    return list(result)


async def get_character(
    db: AsyncSession,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
) -> Character | None:
    return await db.scalar(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == user_id,
        )
    )


async def create_character(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: CharacterCreate,
) -> Character:
    values = build_character_values(payload.model_dump(exclude_none=True))
    character = Character(user_id=user_id, **values)
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character


async def update_character(
    db: AsyncSession,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
    payload: CharacterUpdate,
) -> Character | None:
    character = await get_character(db, user_id, character_id)
    if character is None:
        return None

    values = build_character_values(
        payload.model_dump(exclude_unset=True),
        existing=character,
    )
    for field, value in values.items():
        setattr(character, field, value)

    await db.commit()
    await db.refresh(character)
    return character


async def delete_character(
    db: AsyncSession,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
) -> bool:
    character = await get_character(db, user_id, character_id)
    if character is None:
        return False

    await db.delete(character)
    await db.commit()
    return True
