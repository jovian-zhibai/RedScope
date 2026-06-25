"""Tests for projects, findings, assets APIs."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client):
    res = await client.post("/api/v1/auth/register", json={
        "username": "testproj_user",
        "password": "TestPass123",
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_project(client, auth_headers):
    res = await client.post("/api/v1/projects", json={
        "name": "Test Project",
        "mode": "range",
        "description": "For testing",
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Test Project"
    assert data["mode"] == "range"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client, auth_headers):
    await client.post("/api/v1/projects", json={"name": "P1", "mode": "range"}, headers=auth_headers)
    await client.post("/api/v1/projects", json={"name": "P2", "mode": "combat"}, headers=auth_headers)
    res = await client.get("/api/v1/projects", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["items"]) >= 2


@pytest.mark.asyncio
async def test_get_project(client, auth_headers):
    create_res = await client.post("/api/v1/projects", json={"name": "Detail Test", "mode": "range"}, headers=auth_headers)
    pid = create_res.json()["id"]
    res = await client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Detail Test"


@pytest.mark.asyncio
async def test_create_asset(client, auth_headers):
    create_res = await client.post("/api/v1/projects", json={"name": "Asset Test", "mode": "range"}, headers=auth_headers)
    pid = create_res.json()["id"]
    res = await client.post(f"/api/v1/projects/{pid}/assets", json={
        "asset_type": "ip", "host": "192.168.1.100", "port": 80,
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["host"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_list_assets(client, auth_headers):
    create_res = await client.post("/api/v1/projects", json={"name": "Asset List", "mode": "range"}, headers=auth_headers)
    pid = create_res.json()["id"]
    await client.post(f"/api/v1/projects/{pid}/assets", json={"asset_type": "ip", "host": "10.0.0.1"}, headers=auth_headers)
    res = await client.get(f"/api/v1/projects/{pid}/assets", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_delete_asset_soft(client, auth_headers):
    create_res = await client.post("/api/v1/projects", json={"name": "Del Test", "mode": "range"}, headers=auth_headers)
    pid = create_res.json()["id"]
    asset_res = await client.post(f"/api/v1/projects/{pid}/assets", json={"asset_type": "ip", "host": "10.0.0.99"}, headers=auth_headers)
    aid = asset_res.json()["id"]
    del_res = await client.delete(f"/api/v1/projects/{pid}/assets/{aid}", headers=auth_headers)
    assert del_res.status_code == 200
    list_res = await client.get(f"/api/v1/projects/{pid}/assets", headers=auth_headers)
    hosts = [a["host"] for a in list_res.json()["items"]]
    assert "10.0.0.99" not in hosts


@pytest.mark.asyncio
async def test_create_finding(client, auth_headers):
    create_res = await client.post("/api/v1/projects", json={"name": "Finding Test", "mode": "range"}, headers=auth_headers)
    pid = create_res.json()["id"]
    res = await client.post(f"/api/v1/projects/{pid}/findings", json={
        "title": "SQL Injection in login",
        "vuln_type": "sqli",
        "severity": "critical",
    }, headers=auth_headers)
    assert res.status_code == 200
    assert "id" in res.json()


@pytest.mark.asyncio
async def test_finding_stats(client, auth_headers):
    create_res = await client.post("/api/v1/projects", json={"name": "Stats Test", "mode": "range"}, headers=auth_headers)
    pid = create_res.json()["id"]
    await client.post(f"/api/v1/projects/{pid}/findings", json={"title": "V1", "severity": "critical"}, headers=auth_headers)
    await client.post(f"/api/v1/projects/{pid}/findings", json={"title": "V2", "severity": "high"}, headers=auth_headers)
    res = await client.get(f"/api/v1/projects/{pid}/findings/stats", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 2


@pytest.mark.asyncio
async def test_global_search(client, auth_headers):
    await client.post("/api/v1/projects", json={"name": "SearchMe Project", "mode": "range"}, headers=auth_headers)
    res = await client.get("/api/v1/search?q=SearchMe", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["projects"]) >= 1


@pytest.mark.asyncio
async def test_ai_chat_no_key(client, auth_headers):
    res = await client.post("/api/v1/ai/chat", json={"message": "test"}, headers=auth_headers)
    assert res.status_code == 200
    assert "reply" in res.json()
