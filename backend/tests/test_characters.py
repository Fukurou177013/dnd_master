from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models import Character, User
from tests.fakes import FixedRollGenerator

PASSWORD = "correct horse battery staple"


def character_payload(name: str = "Ariel") -> dict:
    return {
        "name": name,
        "level": 1,
        "species": "Elf",
        "character_class": "Wizard",
        "background": "Sage",
        "ability_score_method": "manual",
        "background_ability_bonus": {"constitution": 2, "intelligence": 1},
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

    response = await client.post("/api/v1/rules/ability-scores/roll")
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
    assert created["data"]["darkvision"] == 60

    response = await client.patch(
        f"/api/v1/characters/{created['id']}",
        json={"level": 5},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["data"]["proficiency_bonus"] == 3
    assert updated["max_hp"] == 27

    response = await client.patch(
        f"/api/v1/characters/{created['id']}",
        json={"species": "Dwarf"},
    )
    assert response.status_code == 200, response.text
    dwarf = response.json()
    assert dwarf["speed"] == 30
    assert dwarf["data"]["darkvision"] == 120


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

    species = {item["name"]: item for item in options["species"]}
    assert set(species) == {
        "Dragonborn",
        "Dwarf",
        "Elf",
        "Gnome",
        "Goliath",
        "Halfling",
        "Human",
        "Orc",
        "Tiefling",
    }
    assert species["Elf"]["speed"] == 30
    assert species["Elf"]["darkvision"] == 60
    assert species["Dwarf"]["darkvision"] == 120
    assert species["Human"]["darkvision"] == 0

    generation = options["ability_generation"]
    assert generation["score_range"] == {"min": 3, "max": 18}
    methods = {method["key"]: method for method in generation["methods"]}
    assert set(methods) == {
        "manual",
        "standard_array",
        "point_buy",
        "roll_4d6",
    }
    assert methods["standard_array"]["values"] == [15, 14, 13, 12, 10, 8]
    assert methods["point_buy"]["budget"] == 27
    assert methods["point_buy"]["costs"]["8"] == 0
    assert methods["point_buy"]["costs"]["15"] == 9
    assert methods["roll_4d6"]["dice"] == {
        "count": 4,
        "sides": 6,
        "drop_lowest": 1,
    }

    backgrounds = {item["name"]: item for item in options["backgrounds"]}
    assert backgrounds["Sage"]["ability_scores"] == [
        "constitution",
        "intelligence",
        "wisdom",
    ]
    bonus = options["background_ability_bonus"]
    assert bonus["max_score"] == 20
    assert bonus["modes"] == [
        {"key": "two_one", "label": "+2 / +1", "values": [2, 1]},
        {"key": "one_one_one", "label": "+1 / +1 / +1", "values": [1, 1, 1]},
    ]


async def test_roll_ability_scores(
    client: AsyncClient,
    roll_generator: FixedRollGenerator,
) -> None:
    await register_and_login(client, "rules@example.com")

    response = await client.post("/api/v1/rules/ability-scores/roll")
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "roll_4d6"
    assert set(body["scores"]) == {
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    }
    assert all(score == 12 for score in body["scores"].values())


async def test_roll_4d6_ability_scores(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["ability_score_method"] = "roll_4d6"
    payload.update(
        {
            "strength": 15,
            "dexterity": 14,
            "constitution": 13,
            "intelligence": 12,
            "wisdom": 10,
            "charisma": 8,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["data"]["ability_score_method"] == "roll_4d6"

    payload = character_payload()
    payload["ability_score_method"] = "roll_4d6"
    payload["strength"] = 2
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


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


async def test_create_requires_ability_score_method(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload.pop("ability_score_method")
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_create_rejects_unknown_ability_score_method(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["ability_score_method"] = "roll_4d6_drop_lowest"
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_standard_array_ability_scores(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["ability_score_method"] = "standard_array"
    payload.update(
        {
            "strength": 8,
            "dexterity": 10,
            "constitution": 14,
            "intelligence": 16,
            "wisdom": 14,
            "charisma": 13,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["data"]["ability_score_method"] == "standard_array"

    payload = character_payload()
    payload["ability_score_method"] = "standard_array"
    payload.update(
        {
            "strength": 9,
            "dexterity": 10,
            "constitution": 14,
            "intelligence": 16,
            "wisdom": 14,
            "charisma": 13,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_point_buy_ability_scores(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["ability_score_method"] = "point_buy"
    payload.update(
        {
            "strength": 15,
            "dexterity": 15,
            "constitution": 17,
            "intelligence": 9,
            "wisdom": 8,
            "charisma": 8,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["data"]["ability_score_method"] == "point_buy"

    payload = character_payload()
    payload["ability_score_method"] = "point_buy"
    payload.update(
        {
            "strength": 15,
            "dexterity": 15,
            "constitution": 17,
            "intelligence": 16,
            "wisdom": 8,
            "charisma": 8,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["ability_score_method"] = "point_buy"
    payload.update(
        {
            "strength": 16,
            "dexterity": 14,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 8,
            "charisma": 8,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_background_bonus_one_one_one(client: AsyncClient) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["background_ability_bonus"] = {
        "constitution": 1,
        "intelligence": 1,
        "wisdom": 1,
    }
    payload.update(
        {
            "strength": 8,
            "dexterity": 14,
            "constitution": 13,
            "intelligence": 17,
            "wisdom": 11,
            "charisma": 10,
        }
    )
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["data"]["background_ability_bonus"] == {
        "strength": 0,
        "dexterity": 0,
        "constitution": 1,
        "intelligence": 1,
        "wisdom": 1,
        "charisma": 0,
    }
    assert created["constitution"] == 13
    assert created["intelligence"] == 17
    assert created["wisdom"] == 11


async def test_background_bonus_rejects_invalid_distribution(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["background_ability_bonus"] = {"strength": 2, "dexterity": 1}
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["background_ability_bonus"] = {"constitution": 2}
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422

    payload = character_payload()
    payload["background_ability_bonus"] = {
        "constitution": 3,
        "intelligence": 0,
        "wisdom": 0,
    }
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_create_requires_background_ability_bonus(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload.pop("background_ability_bonus")
    response = await client.post("/api/v1/characters", json=payload)
    assert response.status_code == 422


async def test_patch_requires_bonus_for_new_background(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()
    url = f"/api/v1/characters/{created['id']}"

    response = await client.patch(url, json={"background": "Soldier"})
    assert response.status_code == 422

    response = await client.patch(
        url,
        json={
            "background": "Soldier",
            "background_ability_bonus": {"strength": 2, "dexterity": 1},
            "strength": 10,
            "dexterity": 15,
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["strength"] == 10
    assert updated["dexterity"] == 15
    assert updated["data"]["background_ability_bonus"] == {
        "strength": 2,
        "dexterity": 1,
        "constitution": 0,
        "intelligence": 0,
        "wisdom": 0,
        "charisma": 0,
    }


async def test_patch_score_keeps_existing_background_bonus(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()
    url = f"/api/v1/characters/{created['id']}"

    response = await client.patch(url, json={"strength": 10})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["strength"] == 10
    assert updated["constitution"] == 12
    assert updated["intelligence"] == 16
    assert updated["data"]["background_ability_bonus"] == {
        "strength": 0,
        "dexterity": 0,
        "constitution": 2,
        "intelligence": 1,
        "wisdom": 0,
        "charisma": 0,
    }


async def test_legacy_character_requires_method_only_when_abilities_change(
    client: AsyncClient,
    db_session,
) -> None:
    await register_and_login(client, "legacy@example.com")
    user = await db_session.scalar(
        select(User).where(User.email == "legacy@example.com")
    )
    assert user is not None

    character = Character(
        user_id=user.id,
        name="Old Hero",
        level=1,
        species="Elf",
        character_class="Wizard",
        background="Sage",
        strength=8,
        dexterity=14,
        constitution=12,
        intelligence=16,
        wisdom=10,
        charisma=10,
        max_hp=7,
        current_hp=7,
        armor_class=12,
        speed=30,
        notes=None,
        data={"skills": ["Arcana", "History"]},
    )
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    url = f"/api/v1/characters/{character.id}"

    response = await client.patch(url, json={"current_hp": 3})
    assert response.status_code == 200, response.text
    assert response.json()["current_hp"] == 3
    assert "ability_score_method" not in response.json()["data"]

    response = await client.patch(url, json={"level": 2})
    assert response.status_code == 200, response.text
    upgraded = response.json()
    assert upgraded["max_hp"] == 12
    assert upgraded["current_hp"] == 3

    response = await client.patch(url, json={"strength": 10})
    assert response.status_code == 422
    assert "метод" in response.json()["detail"].lower()

    response = await client.patch(
        url,
        json={"strength": 10, "ability_score_method": "manual"},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["strength"] == 10
    assert updated["data"]["ability_score_method"] == "manual"


async def test_patch_with_data_keeps_skills_and_method(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()

    response = await client.patch(
        f"/api/v1/characters/{created['id']}",
        json={"data": {"skill_proficiencies": ["Arcana", "History", "Insight"]}},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["data"]["skill_proficiencies"] == [
        "Arcana",
        "History",
        "Insight",
    ]
    assert updated["data"]["ability_score_method"] == "manual"


async def test_patch_class_change_rejects_stale_skills(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "rules@example.com")

    payload = character_payload()
    payload["data"] = {
        "skill_proficiencies": ["Arcana", "History", "Insight"]
    }
    created = (await client.post("/api/v1/characters", json=payload)).json()
    url = f"/api/v1/characters/{created['id']}"

    response = await client.patch(url, json={"character_class": "Barbarian"})
    assert response.status_code == 422

    response = await client.patch(
        url,
        json={
            "character_class": "Barbarian",
            "data": {"skill_proficiencies": ["Arcana", "History"]},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["skill_proficiencies"] == [
        "Arcana",
        "History",
    ]


async def test_patch_rejects_null_ability_score_method(
    client: AsyncClient,
) -> None:
    await register_and_login(client, "hero@example.com")
    created = (
        await client.post("/api/v1/characters", json=character_payload())
    ).json()

    response = await client.patch(
        f"/api/v1/characters/{created['id']}",
        json={"ability_score_method": None},
    )
    assert response.status_code == 422
