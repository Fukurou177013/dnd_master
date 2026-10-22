from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class EmailAlreadyRegisteredError(Exception):
    pass


async def register_user(
    db: AsyncSession,
    email: str,
    password_hash: str,
    display_name: str,
) -> User:
    normalized_email = email.strip().lower()

    existing_user_id = await db.scalar(
        select(User.id).where(User.email == normalized_email)
    )
    if existing_user_id is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=normalized_email,
        password_hash=password_hash,
        display_name=display_name,
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if isinstance(exc.orig, UniqueViolation):
            raise EmailAlreadyRegisteredError from exc
        raise

    await db.refresh(user)
    return user
