from httpx import AsyncClient

PASSWORD = "correct horse battery staple"


async def test_register_login_logout_flow(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": PASSWORD,
            "display_name": "Игрок",
        },
    )
    assert response.status_code == 201, response.text

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    assert "session_token" in response.cookies

    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"

    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 204

    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_duplicate_email_is_rejected(client: AsyncClient) -> None:
    payload = {
        "email": "user@example.com",
        "password": PASSWORD,
        "display_name": "Игрок",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


async def test_wrong_password_is_rejected(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": PASSWORD,
            "display_name": "Игрок",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong password"},
    )
    assert response.status_code == 401


async def test_foreign_origin_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": PASSWORD,
            "display_name": "Игрок",
        },
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


async def test_same_origin_is_allowed(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": PASSWORD,
            "display_name": "Игрок",
        },
        headers={"Origin": "http://test"},
    )
    assert response.status_code == 201, response.text
