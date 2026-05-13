from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "ci-jwt-secret")
os.environ.setdefault("SLACK_SIGNING_SECRET", "ci-slack-secret")
os.environ.setdefault("HMAC_SECRET_KEY", "ci-hmac-secret")

from api.auth import AuthUser
from api.routes import approvals, campaigns
from main import app
from state.db import get_db


class _DummyDB:
    async def get(self, *args, **kwargs):
        return None

    async def execute(self, *args, **kwargs):
        class _R:
            def scalars(self):
                return self

            def all(self):
                return []

        return _R()


def test_openapi_registers_commit13_endpoints() -> None:
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/api/campaigns" in paths
    assert "/api/attacks" in paths
    assert "/api/verdicts" in paths
    assert "/api/vulnerabilities" in paths
    assert "/api/regression/history" in paths
    assert "/api/taxonomy/techniques" in paths
    assert "/api/observability/coverage" in paths
    assert "/api/approvals/attack/{attack_id}" in paths
    assert "/api/slack/webhook" in paths


def test_operator_guard_blocks_campaign_create_without_override() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/campaigns",
        json={
            "execution_mode": "auto",
            "testing_mode": "blackbox",
            "target_category": "prompt_injection",
            "target_url": "http://localhost",
        },
    )
    assert response.status_code in {401, 403}


def test_ciso_guard_applies_on_report_approval() -> None:
    async def _fake_ciso() -> AuthUser:
        return AuthUser(id=uuid.uuid4(), email="ciso@example.com", role="ciso")

    app.dependency_overrides[approvals.require_ciso] = _fake_ciso
    app.dependency_overrides[get_db] = lambda: _DummyDB()

    client = TestClient(app)
    response = client.post(
        f"/api/approvals/report/{uuid.uuid4()}",
        json={"decision": "approve"},
    )
    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_operator_guard_can_be_overridden_for_campaign_mode_path() -> None:
    async def _fake_operator() -> AuthUser:
        return AuthUser(id=uuid.uuid4(), email="op@example.com", role="operator")

    app.dependency_overrides[campaigns.require_operator] = _fake_operator
    app.dependency_overrides[get_db] = lambda: _DummyDB()

    client = TestClient(app)
    response = client.patch(
        f"/api/campaigns/{uuid.uuid4()}/mode",
        json={"execution_mode": "permissions"},
    )
    assert response.status_code == 404

    app.dependency_overrides.clear()
