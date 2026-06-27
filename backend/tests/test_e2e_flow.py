"""端到端流程测试：模拟用户从登录到出报告的完整操作链路。
目标服务器: lab.wangdun.cn:52706
"""

import httpx
import pytest
import time

import os

BASE_URL = os.environ.get("REDSCOPE_TEST_URL", "http://localhost:8000")
ADMIN_PASSWORD = os.environ.get("REDSCOPE_TEST_ADMIN_PASSWORD", "Admin@2026test")
TIMEOUT = 15


@pytest.fixture(scope="module")
def client():
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.fixture(scope="module")
def admin_token(client):
    """登录管理员账号获取token。"""
    res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": ADMIN_PASSWORD,
    })
    if res.status_code != 200:
        pytest.skip(f"无法登录管理员账号: {res.status_code} {res.text[:200]}")
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def test_user_token(client, auth):
    """管理员创建测试用户并用其登录。"""
    username = f"e2e_tester_{int(time.time())}"
    password = "TestPass2026!"

    client.post("/api/v1/auth/users", json={
        "username": username,
        "password": password,
        "display_name": "E2E测试用户",
        "role": "engineer",
    }, headers=auth)

    res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password,
    })
    if res.status_code != 200:
        pytest.skip(f"测试用户登录失败: {res.text[:200]}")
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def user_auth(test_user_token):
    return {"Authorization": f"Bearer {test_user_token}"}


class TestHealthCheck:
    def test_health_endpoint(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["app"] == "RedScope"
        assert "version" in data

    def test_health_includes_db_status(self, client):
        res = client.get("/api/v1/health")
        data = res.json()
        assert "database" in data
        assert "redis" in data


class TestAuthFlow:
    def test_login_wrong_password(self, client):
        res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong_password_123",
        })
        assert res.status_code == 401

    def test_access_without_token(self, client):
        res = client.get("/api/v1/projects")
        assert res.status_code == 401

    def test_access_with_invalid_token(self, client):
        res = client.get("/api/v1/projects", headers={
            "Authorization": "Bearer invalid.token.here",
        })
        assert res.status_code == 401

    def test_get_current_user(self, client, auth):
        res = client.get("/api/v1/auth/me", headers=auth)
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"


class TestFullWorkflow:
    """模拟完整渗透测试流程：创建项目→配边界→加资产→添漏洞→查统计→改状态→搜索→Dashboard。"""

    project_id = None
    asset_id = None
    finding_id = None
    scope_rule_id = None

    def test_01_create_project(self, client, user_auth):
        res = client.post("/api/v1/projects", json={
            "name": "E2E集成测试项目",
            "mode": "range",
            "description": "自动化端到端测试",
            "client_name": "测试客户",
        }, headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "E2E集成测试项目"
        assert data["mode"] == "range"
        TestFullWorkflow.project_id = data["id"]

    def test_02_get_project(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        assert pid is not None
        res = client.get(f"/api/v1/projects/{pid}", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "E2E集成测试项目"
        assert data["asset_count"] == 0

    def test_03_add_scope_rule(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.post(f"/api/v1/projects/{pid}/scope", json={
            "rule_type": "include",
            "target_type": "cidr",
            "target_value": "192.168.0.0/16",
            "description": "内网测试段",
        }, headers=user_auth)
        assert res.status_code == 200
        TestFullWorkflow.scope_rule_id = res.json()["id"]

    def test_04_list_scope_rules(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.get(f"/api/v1/projects/{pid}/scope", headers=user_auth)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) >= 1
        assert any(r["target_value"] == "192.168.0.0/16" for r in items)

    def test_05_create_assets(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.post(f"/api/v1/projects/{pid}/assets", json={
            "asset_type": "ip",
            "host": "192.168.1.100",
            "port": 80,
            "importance": "critical",
        }, headers=user_auth)
        assert res.status_code == 200
        TestFullWorkflow.asset_id = res.json()["id"]

        client.post(f"/api/v1/projects/{pid}/assets", json={
            "asset_type": "ip",
            "host": "192.168.1.101",
            "port": 443,
            "importance": "normal",
        }, headers=user_auth)

    def test_06_list_assets(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.get(f"/api/v1/projects/{pid}/assets", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2

    def test_07_asset_stats(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.get(f"/api/v1/projects/{pid}/assets/stats", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2

    def test_08_create_findings(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        aid = TestFullWorkflow.asset_id

        res = client.post(f"/api/v1/projects/{pid}/findings", json={
            "asset_id": aid,
            "title": "SQL注入 - 登录页面",
            "vuln_type": "sqli",
            "severity": "critical",
            "cvss_score": 9.8,
            "description": "登录接口存在SQL注入漏洞",
            "solution": "使用参数化查询",
            "found_by": "manual",
        }, headers=user_auth)
        assert res.status_code == 200
        TestFullWorkflow.finding_id = res.json()["id"]

        client.post(f"/api/v1/projects/{pid}/findings", json={
            "title": "目录遍历",
            "vuln_type": "path_traversal",
            "severity": "high",
            "description": "通过../可读取任意文件",
        }, headers=user_auth)

        client.post(f"/api/v1/projects/{pid}/findings", json={
            "title": "信息泄露 - Server版本",
            "severity": "low",
            "description": "HTTP响应头暴露Server版本",
        }, headers=user_auth)

    def test_09_list_findings(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.get(f"/api/v1/projects/{pid}/findings", headers=user_auth)
        assert res.status_code == 200
        assert res.json()["total"] >= 3

    def test_10_finding_stats(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.get(f"/api/v1/projects/{pid}/findings/stats", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 3
        assert data["severities"]["critical"] >= 1

    def test_11_get_finding_detail(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        fid = TestFullWorkflow.finding_id
        res = client.get(f"/api/v1/projects/{pid}/findings/{fid}", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "SQL注入 - 登录页面"
        assert data["severity"] == "critical"
        assert data["asset_id"] == TestFullWorkflow.asset_id

    def test_12_update_finding_status(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        fid = TestFullWorkflow.finding_id
        res = client.put(f"/api/v1/projects/{pid}/findings/{fid}", json={
            "fix_status": "fixed",
            "is_verified": True,
        }, headers=user_auth)
        assert res.status_code == 200

        detail = client.get(f"/api/v1/projects/{pid}/findings/{fid}", headers=user_auth).json()
        assert detail["fix_status"] == "fixed"
        assert detail["is_verified"] is True

    def test_13_soft_delete_asset(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        create_res = client.post(f"/api/v1/projects/{pid}/assets", json={
            "asset_type": "ip", "host": "192.168.1.250",
        }, headers=user_auth)
        temp_aid = create_res.json()["id"]

        del_res = client.delete(f"/api/v1/projects/{pid}/assets/{temp_aid}", headers=user_auth)
        assert del_res.status_code == 200

        list_res = client.get(f"/api/v1/projects/{pid}/assets", headers=user_auth)
        hosts = [a["host"] for a in list_res.json()["items"]]
        assert "192.168.1.250" not in hosts

    def test_14_global_search(self, client, user_auth):
        res = client.get("/api/v1/search?q=E2E集成", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert len(data["projects"]) >= 1

    def test_15_dashboard_summary(self, client, user_auth):
        res = client.get("/api/v1/dashboard/summary", headers=user_auth)
        assert res.status_code == 200
        data = res.json()
        assert data["active_projects"] >= 1
        assert data["total_findings"] >= 0

    def test_16_update_project_status(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.put(f"/api/v1/projects/{pid}", json={
            "status": "completed",
        }, headers=user_auth)
        assert res.status_code == 200

    def test_17_scope_changelog(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        res = client.get(f"/api/v1/projects/{pid}/scope/changelog", headers=user_auth)
        assert res.status_code == 200
        assert len(res.json()["items"]) >= 1


class TestEdgeCases:
    """边界条件测试。"""

    def test_search_min_length(self, client, auth):
        res = client.get("/api/v1/search?q=a", headers=auth)
        assert res.status_code == 200
        data = res.json()
        assert data["projects"] == []

    def test_invalid_severity(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        if not pid:
            pytest.skip("需先运行 TestFullWorkflow")
        fid = TestFullWorkflow.finding_id
        res = client.put(f"/api/v1/projects/{pid}/findings/{fid}", json={
            "severity": "super_critical",
        }, headers=user_auth)
        assert res.status_code == 400

    def test_invalid_fix_status(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        fid = TestFullWorkflow.finding_id
        res = client.put(f"/api/v1/projects/{pid}/findings/{fid}", json={
            "fix_status": "nonexistent",
        }, headers=user_auth)
        assert res.status_code == 400

    def test_nonexistent_project(self, client, auth):
        res = client.get("/api/v1/projects/999999", headers=auth)
        assert res.status_code == 404

    def test_nonexistent_finding(self, client, auth):
        res = client.get("/api/v1/projects/1/findings/999999", headers=auth)
        assert res.status_code in (404, 403)

    def test_asset_port_range_validation(self, client, user_auth):
        pid = TestFullWorkflow.project_id
        if not pid:
            pytest.skip("需先运行 TestFullWorkflow")
        aid = TestFullWorkflow.asset_id
        res = client.put(f"/api/v1/projects/{pid}/assets/{aid}", json={
            "port": 99999,
        }, headers=user_auth)
        assert res.status_code == 400
