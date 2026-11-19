import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.rules.character_options import CharacterRulesError
from app.schemas.campaign import (
    CampaignCreate,
    CampaignExchange,
    CampaignMessageCreate,
    CampaignMessagePublic,
    CampaignPublic,
)
from app.services.campaigns import (
    CharacterNotOwnedError,
    create_campaign,
    delete_campaign,
    get_campaign,
    list_campaigns,
    list_messages,
)
from app.services.characters import get_character
from app.services.content_policy import check_content
from app.services.dice import RollGenerator, get_roll_generator
from app.services.game_master import generate_intro_scene, run_turn
from app.services.llm import (
    ChatProvider,
    EmbeddingProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    get_chat_provider,
    get_embedding_provider,
)
from app.services.rate_limit import allow_request

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
Chat = Annotated[ChatProvider, Depends(get_chat_provider)]
Embeddings = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
Rolls = Annotated[RollGenerator, Depends(get_roll_generator)]


@router.get("", response_model=list[CampaignPublic])
async def list_my_campaigns(
    current_user: CurrentUser,
    db: DbSession,
) -> list:
    return await list_campaigns(db, current_user.id)


@router.post(
    "",
    response_model=CampaignPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_campaign(
    payload: CampaignCreate,
    current_user: CurrentUser,
    db: DbSession,
    chat: Chat,
) -> object:
    if not allow_request(current_user.id, settings.chat_rate_limit_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов, попробуйте позже",
        )

    character = await get_character(db, current_user.id, payload.character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Персонаж не найден",
        )
    await db.commit()

    if payload.premise and not check_content(payload.premise).allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Пожелание кампании нарушает правила контента. "
                "Измените пожелание и попробуйте снова."
            ),
        )

    try:
        intro = await generate_intro_scene(
            character=character,
            premise=payload.premise,
            chat=chat,
        )
        return await create_campaign(
            db,
            current_user.id,
            payload,
            intro=intro,
        )
    except CharacterNotOwnedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Персонаж не найден",
        ) from exc
    except ProviderTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Мастер не ответил вовремя. Кампания не создана, повторите запрос.",
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Мастер временно недоступен. Кампания не создана, повторите запрос.",
        ) from exc


@router.get("/{campaign_id}", response_model=CampaignPublic)
async def get_my_campaign(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> object:
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кампания не найдена",
        )
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_campaign(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    deleted = await delete_campaign(db, current_user.id, campaign_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кампания не найдена",
        )


@router.get(
    "/{campaign_id}/messages",
    response_model=list[CampaignMessagePublic],
)
async def get_my_campaign_messages(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list:
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кампания не найдена",
        )
    return await list_messages(db, campaign.id, limit=limit)


@router.post(
    "/{campaign_id}/messages",
    response_model=CampaignExchange,
)
async def send_campaign_message(
    campaign_id: uuid.UUID,
    payload: CampaignMessageCreate,
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
    chat: Chat,
    embeddings: Embeddings,
    roll_generator: Rolls,
) -> CampaignExchange:
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кампания не найдена",
        )
    if not allow_request(current_user.id, settings.chat_rate_limit_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много сообщений, попробуйте позже",
        )

    character = await get_character(db, current_user.id, campaign.character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Персонаж не найден",
        )

    try:
        return await run_turn(
            db,
            background_tasks=background_tasks,
            campaign=campaign,
            character=character,
            payload=payload,
            chat=chat,
            embeddings=embeddings,
            roll_generator=roll_generator,
        )
    except CharacterRulesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ProviderTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Мастер не ответил вовремя. Сообщение сохранено, повторите запрос.",
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Мастер временно недоступен. Сообщение сохранено, повторите запрос.",
        ) from exc
