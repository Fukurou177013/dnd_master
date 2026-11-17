import asyncio
import os
import sys

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (  # noqa: F401
    Campaign,
    CampaignMemory,
    CampaignMessage,
    Character,
    SrdChunk,
    User,
    UserSession,
)
from app.services.dice import get_roll_generator
from app.services.llm import get_chat_provider, get_embedding_provider
from app.services.rate_limit import reset_rate_limits
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider, FixedRollGenerator

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "dnd_test")
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+psycopg://dnd:dnd@localhost:5433/{TEST_DB_NAME}",
)
TEST_ADMIN_URL = os.environ.get(
    "TEST_ADMIN_URL",
    "postgresql://dnd:dnd@localhost:5433/postgres",
)

engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _ensure_test_database() -> None:
    with psycopg.connect(TEST_ADMIN_URL, autocommit=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TEST_DB_NAME,),
        ).fetchone()
        if exists is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB_NAME))
            )


async def _create_schema() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


def pytest_sessionstart(session) -> None:
    del session
    _ensure_test_database()
    asyncio.run(_create_schema(), loop_factory=asyncio.SelectorEventLoop)


@pytest.fixture(autouse=True)
async def clean_database():
    reset_rate_limits()
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE users, srd_chunks CASCADE"))
    yield


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def fake_chat() -> FakeChatProvider:
    return FakeChatProvider()


@pytest.fixture
def fake_embeddings() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def roll_generator() -> FixedRollGenerator:
    return FixedRollGenerator()


@pytest.fixture
async def client(
    db_session,
    fake_chat: FakeChatProvider,
    fake_embeddings: FakeEmbeddingProvider,
    roll_generator: FixedRollGenerator,
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chat_provider] = lambda: fake_chat
    app.dependency_overrides[get_embedding_provider] = lambda: fake_embeddings
    app.dependency_overrides[get_roll_generator] = lambda: roll_generator
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

