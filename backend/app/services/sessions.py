import uuid
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSession


async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    token_hash: bytes,
    expires_at: datetime,
    user_agent: str | None,
    ip: str | None,
) -> UserSession:
    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session_by_token_hash(db: AsyncSession, token_hash: bytes) -> None:
    await db.execute(delete(UserSession).where(UserSession.token_hash == token_hash))
    await db.commit()
