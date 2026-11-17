import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Character, User
from app.rules.character_options import CharacterRulesError
from app.schemas.character import (
    CharacterCreate,
    CharacterPublic,
    CharacterUpdate,
)
from app.services.characters import (
    create_character,
    delete_character,
    get_character,
    list_characters,
    update_character,
)

router = APIRouter(prefix="/characters", tags=["characters"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[CharacterPublic])
async def list_my_characters(
    current_user: CurrentUser,
    db: DbSession,
) -> list[Character]:
    return await list_characters(db, current_user.id)


@router.post(
    "",
    response_model=CharacterPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_character(
    payload: CharacterCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Character:
    try:
        return await create_character(db, current_user.id, payload)
    except CharacterRulesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/{character_id}", response_model=CharacterPublic)
async def get_my_character(
    character_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> Character:
    character = await get_character(db, current_user.id, character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Персонаж не найден",
        )
    return character


@router.patch("/{character_id}", response_model=CharacterPublic)
async def update_my_character(
    character_id: uuid.UUID,
    payload: CharacterUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Character:
    try:
        character = await update_character(
            db,
            current_user.id,
            character_id,
            payload,
        )
    except CharacterRulesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Персонаж не найден",
        )
    return character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_character(
    character_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    deleted = await delete_character(db, current_user.id, character_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Персонаж не найден",
        )
