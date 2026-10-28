from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserPublic
from app.services.auth import (
    EmailAlreadyRegisteredError,
    get_user_by_email,
    register_user,
)
from app.services.sessions import create_session, delete_session_by_token_hash

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


@router.post("/login", response_model=UserPublic)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    user = await get_user_by_email(db, str(payload.email))

    if user is None:
        await run_in_threadpool(verify_password, payload.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    password_is_valid = await run_in_threadpool(
        verify_password, payload.password, user.password_hash
    )
    if not password_is_valid or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = generate_session_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.session_ttl_days)

    await create_session(
        db,
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )

    return user


@router.get("/me", response_model=UserPublic)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    session_token: Annotated[
        str | None, Cookie(alias=SESSION_COOKIE_NAME)
    ] = None,
) -> None:
    if session_token is not None:
        await delete_session_by_token_hash(db, hash_session_token(session_token))

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
