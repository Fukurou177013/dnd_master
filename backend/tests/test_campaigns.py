from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.config import EMBEDDING_DIMENSIONS
from app.main import app
from app.models import SrdChunk
from app.services.campaigns import get_campaign, list_messages
from app.services.game_master import _ensure_assistant_message
from app.services.llm import ProviderTimeoutError, ProviderUnavailableError
from tests.fakes import FakeChatProvider, FixedRollGenerator

PASSWORD = "correct horse battery staple"


def character_payload() -> dict:
    return {
        "name": "Ariel",
        "level": 1,
        "species": "Elf",
        "character_class": "Wizard",
        "background": "Sage",
        "strength": 8,
        "dexterity": 14,
        "constitution": 12,
        "intelligence": 16,
        "wisdom": 10,
        "charisma": 10,
        "current_hp": 7,
        "data": {"skills": ["Arcana", "History"]},
    }


def campaign_payload(character_id: str, name: str = "Lost Mine") -> dict:
    return {"name": name, "character_id": character_id}


async def register_and_login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": "Test User",
        },
    )
    assert response.status_code == 201, response.text
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text


async def create_character(client: AsyncClient) -> str:
    response = await client.post("/api/v1/characters", json=character_payload())
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def create_campaign(client: AsyncClient, character_id: str) -> str:
    response = await client.post(
        "/api/v1/campaigns",
        json=campaign_payload(character_id),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def setup_campaign(client: AsyncClient) -> tuple[str, str]:
    await register_and_login(client, "hero@example.com")
    character_id = await create_character(client)
    campaign_id = await create_campaign(client, character_id)
    return character_id, campaign_id


async def add_srd_chunk(db_session) -> SrdChunk:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = 1.0
    chunk = SrdChunk(
        chunk_key="test-chunk-1",
        source="SRD 5.2.1",
        section="Using Ability Scores / Ability Checks",
        title="Ability Checks",
        content="An ability check tests a character's or monster's innate talent.",
        embedding=vector,
        license="CC BY 4.0",
        chunk_metadata={"source_url": "https://example.com/srd"},
    )
    db_session.add(chunk)
    await db_session.commit()
    await db_session.refresh(chunk)
    return chunk


async def test_campaigns_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/campaigns")
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "Campaign", "character_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 401


async def test_create_and_list_campaign(client: AsyncClient) -> None:
    character_id, campaign_id = await setup_campaign(client)

    response = await client.get("/api/v1/campaigns")
    assert response.status_code == 200
    campaigns = response.json()
    assert len(campaigns) == 1
    assert campaigns[0]["id"] == campaign_id
    assert campaigns[0]["character_id"] == character_id
    assert campaigns[0]["summary"]["facts"] == []

    response = await client.delete(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 204

    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 404


async def test_campaign_rejects_foreign_character(client: AsyncClient) -> None:
    await register_and_login(client, "owner@example.com")
    character_id = await create_character(client)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as other_client:
        await register_and_login(other_client, "stranger@example.com")
        response = await other_client.post(
            "/api/v1/campaigns",
            json=campaign_payload(character_id),
        )
        assert response.status_code == 404


async def test_campaigns_are_isolated_between_users(client: AsyncClient) -> None:
    _, campaign_id = await setup_campaign(client)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as other_client:
        await register_and_login(other_client, "stranger@example.com")

        response = await other_client.get(f"/api/v1/campaigns/{campaign_id}")
        assert response.status_code == 404

        response = await other_client.get(
            f"/api/v1/campaigns/{campaign_id}/messages"
        )
        assert response.status_code == 404

        response = await other_client.post(
            f"/api/v1/campaigns/{campaign_id}/messages",
            json={"content": "Привет"},
        )
        assert response.status_code == 404


async def test_chat_returns_server_roll_sources_and_memory(
    client: AsyncClient,
    db_session,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)
    chunk = await add_srd_chunk(db_session)

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я осматриваю комнату.",
            "client_message_id": "message-1",
            "check": {"ability": "wisdom", "skill": "Perception", "dc": 10},
        },
    )
    assert response.status_code == 200, response.text
    exchange = response.json()

    roll = exchange["assistant_message"]["roll"]
    assert roll["d20"] == 20
    assert roll["ability"] == "wisdom"
    assert roll["skill"] == "Perception"
    assert roll["modifier"] == 0
    assert roll["total"] == 20
    assert roll["success"] is True
    assert exchange["assistant_message"]["content"] == fake_chat.answer
    assert exchange["assistant_message"]["sources"][0]["id"] == str(chunk.id)
    assert exchange["assistant_message"]["sources"][0]["license"] == "CC BY 4.0"
    assert exchange["memory_update_scheduled"] is True

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["roll"] is None
    assert messages[1]["roll"]["d20"] == 20
    assert messages[1]["sources"][0]["section"] == chunk.section

    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    summary = response.json()["summary"]
    assert summary["facts"] == ["Герой вошёл в подземелье"]
    assert summary["open_threads"] == ["Дверь заперта"]


async def test_chat_is_idempotent_by_client_message_id(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)
    payload = {
        "content": "Я иду вперёд.",
        "client_message_id": "same-message",
    }

    first = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json=payload,
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json=payload,
    )
    assert second.status_code == 200, second.text
    assert second.json()["assistant_message"]["id"] == first.json()["assistant_message"]["id"]

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    assert len(response.json()) == 2

    answer_calls = [call for call in fake_chat.calls if "Верни только JSON" not in call[0].content]
    assert len(answer_calls) == 1


async def test_chat_saves_user_message_when_provider_fails(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)
    fake_chat.fail_next = ProviderUnavailableError("down")

    payload = {
        "content": "Я открываю дверь.",
        "client_message_id": "retry-me",
    }
    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json=payload,
    )
    assert response.status_code == 503
    assert "Сообщение сохранено" in response.json()["detail"]

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    messages = response.json()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    user_message_id = messages[0]["id"]

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json=payload,
    )
    assert response.status_code == 200, response.text

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    messages = response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["id"] == user_message_id


async def test_chat_rejects_skill_ability_mismatch(
    client: AsyncClient,
) -> None:
    _, campaign_id = await setup_campaign(client)

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я прислушиваюсь.",
            "check": {"ability": "strength", "skill": "Perception", "dc": 10},
        },
    )
    assert response.status_code == 422

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    assert response.json() == []


async def test_chat_without_retrieval_or_check_still_answers(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я оглядываюсь.",
            "client_message_id": "no-check",
        },
    )
    assert response.status_code == 200, response.text
    exchange = response.json()
    assert exchange["assistant_message"]["roll"] is None
    assert exchange["assistant_message"]["sources"] == []
    assert exchange["memory_update_scheduled"] is True

    answer_system = next(
        call[0].content
        for call in fake_chat.calls
        if "Верни только JSON" not in call[0].content
    )
    assert "Фрагменты SRD не найдены" in answer_system
    assert "Проверка не выполнялась" in answer_system


async def test_chat_handles_provider_timeout(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)
    fake_chat.fail_next = ProviderTimeoutError("timeout")

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я жду.",
            "client_message_id": "timeout-me",
        },
    )
    assert response.status_code == 504

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    assert len(response.json()) == 1


async def test_memory_failure_does_not_remove_messages(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)
    fake_chat.fail_next_summary = ProviderUnavailableError("summary down")

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я иду дальше.",
            "client_message_id": "memory-fail",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["memory_update_scheduled"] is True

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    assert len(response.json()) == 2

    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.json()["summary"]["facts"] == []


async def test_failed_check_is_recorded(
    client: AsyncClient,
    roll_generator: FixedRollGenerator,
) -> None:
    _, campaign_id = await setup_campaign(client)
    roll_generator.d20 = 1

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я пытаюсь вспомнить.",
            "client_message_id": "failed-roll",
            "check": {"ability": "intelligence", "skill": "Arcana", "dc": 15},
        },
    )
    assert response.status_code == 200, response.text
    roll = response.json()["assistant_message"]["roll"]
    assert roll["d20"] == 1
    assert roll["modifier"] == 5
    assert roll["total"] == 6
    assert roll["success"] is False


async def test_memory_failure_keeps_previous_summary(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я вхожу внутрь.",
            "client_message_id": "first-turn",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["memory_update_scheduled"] is True

    fake_chat.fail_next_summary = ProviderUnavailableError("summary down")
    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я иду дальше.",
            "client_message_id": "second-turn",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["memory_update_scheduled"] is True

    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.json()["summary"]["facts"] == ["Герой вошёл в подземелье"]


async def test_malformed_summary_does_not_break_successful_exchange(
    client: AsyncClient,
    fake_chat: FakeChatProvider,
) -> None:
    _, campaign_id = await setup_campaign(client)
    fake_chat.summary_response = "Мастер забыл формат JSON"

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={
            "content": "Я осматриваюсь.",
            "client_message_id": "summary-garbage",
        },
    )
    assert response.status_code == 200, response.text
    exchange = response.json()
    assert exchange["memory_update_scheduled"] is True
    assert exchange["assistant_message"]["content"] == fake_chat.answer

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/messages")
    assert [message["role"] for message in response.json()] == [
        "user",
        "assistant",
    ]

    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.json()["summary"]["facts"] == []


async def test_replayed_turn_does_not_duplicate_assistant_message(
    client: AsyncClient,
    db_session,
) -> None:
    _, campaign_id = await setup_campaign(client)

    response = await client.post(
        f"/api/v1/campaigns/{campaign_id}/messages",
        json={"content": "Я иду вперёд.", "client_message_id": "dedupe"},
    )
    assert response.status_code == 200, response.text

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    user_id = UUID(me.json()["id"])

    campaign = await get_campaign(db_session, user_id, UUID(campaign_id))
    assert campaign is not None
    messages = await list_messages(db_session, campaign.id, limit=10)
    assert [message.role for message in messages] == ["user", "assistant"]

    duplicate = await _ensure_assistant_message(
        db_session,
        campaign=campaign,
        user_message=messages[0],
        content="Дублирующий ответ",
        roll=None,
        sources=[],
    )

    assert duplicate.id == messages[1].id
    assert duplicate.content == messages[1].content

    after = await list_messages(db_session, campaign.id, limit=10)
    assert len(after) == 2
