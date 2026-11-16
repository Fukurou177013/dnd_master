from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.characters import router as characters_router
from app.api.v1.rules import router as rules_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(characters_router)
router.include_router(campaigns_router)
router.include_router(rules_router)
