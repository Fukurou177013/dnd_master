from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import User
from app.rules.character_options import character_options
from app.schemas.character import AbilityScoreRoll
from app.services.dice import (
    RollGenerator,
    get_roll_generator,
    roll_ability_scores,
)

router = APIRouter(prefix="/rules", tags=["rules"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Rolls = Annotated[RollGenerator, Depends(get_roll_generator)]


@router.get("/character-options")
async def get_character_options(current_user: CurrentUser) -> dict[str, Any]:
    del current_user
    options = character_options()
    options["limits"] = {"max_message_length": settings.max_message_length}
    return options


@router.post("/ability-scores/roll", response_model=AbilityScoreRoll)
async def roll_character_ability_scores(
    current_user: CurrentUser,
    generator: Rolls,
) -> dict[str, Any]:
    del current_user
    return {"method": "roll_4d6", "scores": roll_ability_scores(generator)}
