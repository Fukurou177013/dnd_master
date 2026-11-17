from httpx import ASGITransport, AsyncClient

from app.main import app

PASSWORD = "correct horse battery staple"


def character_payload(name: str = "Ariel") -> dict:
    return {
        "name": name,
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
        "max_hp": 7,
        "current_hp": 7,
        "armor_class": 12,
        "speed": 30,
        "notes": "Test character",
        "data": {"skills": ["Arcana", "History"]},
    }


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


async def test_characters_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/characters")
    assert response.status_code == 401

    response = await client.post("/api/v1/characters", json=character_payload())
    assert response.status_code == 401


async def test_create_and_list_character(client: AsyncClient) -> None:
    await register_and_login(client, "hero@example.com")

    response = await client.post("/api/v1/characters", json=character_payload())
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["name"] == "Ariel"
    assert created["id"]
    assert "password_hash" not in created

    response = await client.get("/api/v1/characters")
    assert response.status_code == 200
    characters = response.json()
    assert len(characters) == 1
    assert characters[0]["id"] == created["id"]


async def test_get_update_and_delete_character(client: AsyncClient) -> None:
    await register_and_login(client, "hero@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()
    character_id = created["id"]

    response = await client.get(f"/api/v1/characters/{character_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Ariel"

    response = await client.patch(
        f"/api/v1/characters/{character_id}",
        json={"name": "Ariel the Brave", "current_hp": 5},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Ariel the Brave"
    assert updated["current_hp"] == 5

    response = await client.delete(f"/api/v1/characters/{character_id}")
    assert response.status_code == 204

    response = await client.get(f"/api/v1/characters/{character_id}")
    assert response.status_code == 404


async def test_user_cannot_access_another_users_character(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "owner@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()
    character_id = created["id"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as other_client:
        await register_and_login(other_client, "stranger@example.com")

        response = await other_client.get(f"/api/v1/characters/{character_id}")
        assert response.status_code == 404

        response = await other_client.patch(
            f"/api/v1/characters/{character_id}",
            json={"name": "Stolen"},
        )
        assert response.status_code == 404

        response = await other_client.delete(f"/api/v1/characters/{character_id}")
        assert response.status_code == 404


async def test_list_returns_only_current_users_characters(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "owner@example.com")
    await client.post("/api/v1/characters", json=character_payload("Owner Hero"))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as other_client:
        await register_and_login(other_client, "stranger@example.com")
        await other_client.post(
            "/api/v1/characters",
            json=character_payload("Stranger Hero"),
        )

        response = await other_client.get("/api/v1/characters")
        assert response.status_code == 200
        characters = response.json()
        assert len(characters) == 1
        assert characters[0]["name"] == "Stranger Hero"


async def test_character_validation(client: AsyncClient) -> None:
    await register_and_login(client, "hero@example.com")

    payload = character_payload()
    payload["level"] = 21
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["strength"] = 0
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["current_hp"] = -1
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_patch_rejects_null_for_required_field(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "hero@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()

    response = await client.patch(
        f"/api/v1/characters/{created['id']}",
        json={"name": None},
    )
    assert response.status_code == 422


async def test_character_rules_derive_server_values(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["max_hp"] = 999
    payload["armor_class"] = 99
    payload["speed"] = 99

    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 201, response.text
    created = response.json()

    assert created["max_hp"] == 7
    assert created["armor_class"] == 12
    assert created["speed"] == 30
    assert created["data"]["ability_modifiers"]["intelligence"] == 3
    assert created["data"]["proficiency_bonus"] == 2
    assert created["data"]["skill_proficiencies"] == ["Arcana", "History"]
    assert created["data"]["skill_modifiers"]["Arcana"] == 5
    assert created["data"]["passive_perception"] == 10

    response = await client.patch(
        f"/api/v1/characters/{created['id']}",
        json={"level": 5},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["data"]["proficiency_bonus"] == 3
    assert updated["max_hp"] == 27


async def test_character_rejects_invalid_srd_options(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["species"] = "Klingon"
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["data"] = {"skills": ["Stealth"]}
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["current_hp"] = 8
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_character_options_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/rules/character-options")
    assert response.status_code == 401


async def test_character_options_catalog(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")
    response = await client.get("/api/v1/rules/character-options")
    assert response.status_code == 200
    options = response.json()
    assert any(species["name"] == "Elf" for species in options["species"])
    assert any(item["name"] == "Wizard" for item in options["classes"])
    assert any(item["name"] == "Sage" for item in options["backgrounds"])


async def test_character_class_skill_limit_excludes_background_skills(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["data"] = {
        "skills": ["Arcana", "History", "Insight", "Investigation"]
    }
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 201, response.text

    payload = character_payload()
    payload["data"] = {
        "skills": ["Arcana", "History", "Insight", "Investigation", "Medicine"]
    }
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422
