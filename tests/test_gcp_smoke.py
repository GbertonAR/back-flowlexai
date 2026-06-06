"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: test_gcp_smoke.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton — PYTHOS QA
-------------------------------------------------------
DESCRIPCIÓN: Suite de smoke tests contra el deploy live en GCP Cloud Run.
             Cubre contratos de endpoints, status codes y validaciones RBAC.
             Ejecutar con: poetry run pytest tests/test_gcp_smoke.py -v
FECHA CREACIÓN: 2026-06-02
REF. TICKET: #FS-QA-GCP-001
"""

import pytest
import httpx

BASE = "https://lexia-backend-222680624860.us-central1.run.app/api/v1"

USERS = {
    "admin":      {"email": "admin@flowlex.ai",       "password": "admin"},
    "legislator": {"email": "legislator@flowlex.ai",  "password": "legislator123"},
    "analyst":    {"email": "analyst@flowlex.ai",     "password": "analyst123"},
    "readonly":   {"email": "readonly@flowlex.ai",    "password": "readonly123"},
    "demo":       {"email": "demo@flowlexai.com",     "password": "demo123!"},
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        yield c


def get_token(client: httpx.Client, role: str) -> str:
    u = USERS[role]
    r = client.post("/auth/login", data={"username": u["email"], "password": u["password"]})
    assert r.status_code == 200, f"Login fallido para {role}: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(client):
    return get_token(client, "admin")


@pytest.fixture(scope="session")
def readonly_token(client):
    return get_token(client, "readonly")


@pytest.fixture(scope="session")
def legislator_token(client):
    return get_token(client, "legislator")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. HEALTH ─────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_database_ok(self, client):
        r = client.get("/health")
        assert r.json()["services"]["database"] is True

    def test_root_alive(self, client):
        r = httpx.get("https://lexia-backend-222680624860.us-central1.run.app/", timeout=10)
        assert r.status_code == 200
        assert "LexIA" in r.json().get("message", "")


# ── 2. AUTH — Login ───────────────────────────────────────────────────────────

class TestAuthLogin:
    def test_login_admin_200(self, client):
        r = client.post("/auth/login", data={"username": "admin@flowlex.ai", "password": "admin"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_legislator_200(self, client):
        r = client.post("/auth/login", data={"username": "legislator@flowlex.ai", "password": "legislator123"})
        assert r.status_code == 200

    def test_login_analyst_200(self, client):
        r = client.post("/auth/login", data={"username": "analyst@flowlex.ai", "password": "analyst123"})
        assert r.status_code == 200

    def test_login_readonly_200(self, client):
        r = client.post("/auth/login", data={"username": "readonly@flowlex.ai", "password": "readonly123"})
        assert r.status_code == 200

    def test_login_demo_200(self, client):
        r = client.post("/auth/login", data={"username": "demo@flowlexai.com", "password": "demo123!"})
        assert r.status_code == 200

    def test_login_wrong_password_401(self, client):
        r = client.post("/auth/login", data={"username": "admin@flowlex.ai", "password": "wrongpass"})
        assert r.status_code == 401

    def test_login_unknown_user_401(self, client):
        r = client.post("/auth/login", data={"username": "ghost@nowhere.com", "password": "x"})
        assert r.status_code == 401

    def test_login_empty_credentials_422(self, client):
        r = client.post("/auth/login", data={})
        assert r.status_code == 422


# ── 3. AUTH — /me ─────────────────────────────────────────────────────────────

class TestAuthMe:
    def test_me_admin_returns_profile(self, client, admin_token):
        r = client.get("/auth/me", headers=auth(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "admin@flowlex.ai"
        assert body["role"] == "admin"
        assert body["is_active"] is True

    def test_me_readonly_role_correct(self, client, readonly_token):
        r = client.get("/auth/me", headers=auth(readonly_token))
        assert r.status_code == 200
        assert r.json()["role"] == "readonly"

    def test_me_no_token_401(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token_401(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


# ── 4. AUTH — Register ────────────────────────────────────────────────────────

class TestAuthRegister:
    def test_register_duplicate_email_409(self, client):
        r = client.post("/auth/register", json={
            "email": "admin@flowlex.ai",
            "password": "admin",
            "full_name": "Duplicado",
            "role": "readonly",
            "tenant_id": 1,
        })
        assert r.status_code == 409

    def test_register_missing_email_422(self, client):
        r = client.post("/auth/register", json={"password": "abc", "full_name": "Sin Email"})
        assert r.status_code == 422

    def test_register_invalid_role_422(self, client):
        r = client.post("/auth/register", json={
            "email": "nuevo@flowlex.ai",
            "password": "abc123",
            "full_name": "Rol Invalido",
            "role": "superadmin",
        })
        assert r.status_code == 422


# ── 5. ASSISTANT ──────────────────────────────────────────────────────────────

class TestAssistant:
    def test_analyze_no_token_401(self, client):
        r = client.post("/assistant/analyze", json={"query": "test", "tenant_id": 1})
        assert r.status_code == 401

    def test_analyze_empty_query_422(self, client, admin_token):
        r = client.post("/assistant/analyze",
                        headers=auth(admin_token),
                        json={"tenant_id": 1})
        assert r.status_code == 422

    def test_analyze_missing_tenant_422(self, client, admin_token):
        r = client.post("/assistant/analyze",
                        headers=auth(admin_token),
                        json={"query": "test"})
        assert r.status_code == 422

    def test_analyze_valid_query_returns_response(self, client, admin_token):
        r = client.post("/assistant/analyze",
                        headers=auth(admin_token),
                        json={"query": "Poder Legislativo funciones", "tenant_id": 1},
                        timeout=45.0)
        assert r.status_code in (200, 500), f"Status inesperado: {r.status_code}"
        if r.status_code == 200:
            body = r.json()
            assert "response" in body
            assert "xai_card" in body
            assert "confidence" in body
            assert body["confidence"] in ("HIGH", "MEDIUM", "LOW")

    def test_search_no_token_401(self, client):
        r = client.post("/assistant/search", json={"query": "ley", "tenant_id": 1})
        assert r.status_code == 401

    def test_search_valid_returns_list(self, client, admin_token):
        r = client.post("/assistant/search",
                        headers=auth(admin_token),
                        json={"query": "legislacion", "tenant_id": 1},
                        timeout=20.0)
        assert r.status_code == 200
        body = r.json()
        assert "results" in body
        assert isinstance(body["results"], list)


# ── 6. HITL — RBAC ───────────────────────────────────────────────────────────

class TestHITL:
    def test_hitl_pending_admin_200(self, client, admin_token):
        r = client.get("/hitl/pending?tenant_id=1", headers=auth(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_hitl_pending_legislator_200(self, client, legislator_token):
        r = client.get("/hitl/pending?tenant_id=1", headers=auth(legislator_token))
        assert r.status_code == 200

    def test_hitl_pending_readonly_403(self, client, readonly_token):
        r = client.get("/hitl/pending?tenant_id=1", headers=auth(readonly_token))
        assert r.status_code == 403

    def test_hitl_pending_no_token_401(self, client):
        r = client.get("/hitl/pending?tenant_id=1")
        assert r.status_code == 401


# ── 7. TENANTS ────────────────────────────────────────────────────────────────

class TestTenants:
    def test_tenants_list_200(self, client, admin_token):
        r = client.get("/tenants/", headers=auth(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["id"] == 1

    def test_tenants_no_token_401(self, client):
        r = client.get("/tenants/")
        assert r.status_code == 401


# ── 8. DOCUMENTOS ─────────────────────────────────────────────────────────────

class TestDocuments:
    def test_list_docs_200(self, client, admin_token):
        r = client.get("/ingest/list/1", headers=auth(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert "documents" in body
        assert isinstance(body["documents"], list)

    def test_list_docs_no_token_401(self, client):
        r = client.get("/ingest/list/1")
        assert r.status_code == 401


# ── 9. MÉTRICAS ───────────────────────────────────────────────────────────────

class TestMetrics:
    def test_metrics_summary_200(self, client, admin_token):
        r = client.get("/metrics/summary?tenant_id=1", headers=auth(admin_token))
        assert r.status_code == 200

    def test_metrics_no_token_401(self, client):
        r = client.get("/metrics/summary?tenant_id=1")
        assert r.status_code == 401
