from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SESSION_COOKIE_NAME, hash_session_token
from app.db.session import get_db
from app.models import User, UserSession


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    session_token: Annotated[
        str | None, Cookie(alias=SESSION_COOKIE_NAME)
    ] = None,
) -> User:
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )

    token_hash = hash_session_token(session_token)
    user = await db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > func.now(),
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия недействительна или истекла",
        )

    return user
