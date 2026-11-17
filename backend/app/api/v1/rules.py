from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import User
from app.rules.character_options import character_options

router = APIRouter(prefix="/rules", tags=["rules"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/character-options")
async def get_character_options(current_user: CurrentUser) -> dict[str, Any]:
    del current_user
    options = character_options()
    options["limits"] = {"max_message_length": settings.max_message_length}
    return options
