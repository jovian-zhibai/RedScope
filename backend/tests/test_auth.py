"""Tests for auth API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import init_db, engine


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_success(client):
    res = await client.post("/api/v1/auth/register", json={
        "username": "testuser001",
        "password": "Test1234pass",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "testuser001"


@pytest.mark.asyncio
async def test_register_short_password(client):
    res = await client.post("/api/v1/auth/register", json={
        "username": "testuser002",
        "password": "short",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_register_numeric_password(client):
    res = await client.post("/api/v1/auth/register", json={
        "username": "testuser003",
        "password": "12345678",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_register_short_username(client):
    res = await client.post("/api/v1/auth/register", json={
        "username": "ab",
        "password": "Test1234pass",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/v1/auth/register", json={
        "username": "dupuser",
        "password": "Test1234pass",
    })
    res = await client.post("/api/v1/auth/register", json={
        "username": "dupuser",
        "password": "Test1234pass",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "username": "loginuser",
        "password": "Test1234pass",
    })
    res = await client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "Test1234pass",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "username": "loginuser2",
        "password": "Test1234pass",
    })
    res = await client.post("/api/v1/auth/login", json={
        "username": "loginuser2",
        "password": "wrongpassword1",
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authorized(client):
    reg = await client.post("/api/v1/auth/register", json={
        "username": "meuser",
        "password": "Test1234pass",
    })
    token = reg.json()["access_token"]
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == "meuser"


@pytest.mark.asyncio
async def test_change_password(client):
    reg = await client.post("/api/v1/auth/register", json={
        "username": "pwduser",
        "password": "Test1234pass",
    })
    token = reg.json()["access_token"]
    res = await client.post("/api/v1/auth/change-password", json={
        "old_password": "Test1234pass",
        "new_password": "NewPass5678",
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    login_res = await client.post("/api/v1/auth/login", json={
        "username": "pwduser",
        "password": "NewPass5678",
    })
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["app"] == "RedScope"


@pytest.mark.asyncio
async def test_search_requires_min_length(client):
    reg = await client.post("/api/v1/auth/register", json={
        "username": "searchuser",
        "password": "Test1234pass",
    })
    token = reg.json()["access_token"]
    res = await client.get("/api/v1/search?q=a", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["projects"] == []
