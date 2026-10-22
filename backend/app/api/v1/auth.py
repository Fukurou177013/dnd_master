from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import hash_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserPublic
from app.services.auth import EmailAlreadyRegisteredError, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    password_hash = await run_in_threadpool(hash_password, payload.password)

    try:
        return await register_user(
            db,
            email=str(payload.email),
            password_hash=password_hash,
            display_name=payload.display_name,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email уже зарегистрирован",
        ) from exc
