from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import pytest
from langgraph.graph import END

os.environ.setdefault("OPENROUTER_API_KEY", "mock")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("TARGET_BASE_URL", "http://localhost:8080")
os.environ.setdefault("SESSION_COOKIE", "PHPSESSID=test")
os.environ.setdefault("CSRF_TOKEN", "test_csrf")
os.environ.setdefault("SESSION_PATIENT_UUID", "aaaaaaaa-0000-0000-0000-000000000001")
os.environ.setdefault("VICTIM_UUID", "bbbbbbbb-0000-0000-0000-000000000002")
os.environ.setdefault("SLACK_WEBHOOK_URL", "https://example.com/webhook")
os.environ.setdefault("APPROVAL_CHANNEL", "#security")
os.environ.setdefault("HMAC_SECRET_KEY", "ci-test-secret")

from orchestration.graph import AgentGraph


class _FakeApproval:
    def __init__(self, decision: str, edited_sequence=None):
        self.decision = decision
        self.edited_sequence = edited_sequence


def _build_graph() -> AgentGraph:
    return AgentGraph.__new__(AgentGraph)


def test_route_after_orchestrate_done_goes_end() -> None:
    graph = _build_graph()
    assert graph._route_after_orchestrate({"done": True}) == END


def test_route_after_generate_attack_permissions_requires_approval() -> None:
    graph = _build_graph()
    assert graph._route_after_generate_attack({"execution_mode": "permissions"}) == "await_approval"
    assert graph._route_after_generate_attack({"execution_mode": "auto"}) == "execute_attack"


def test_route_after_await_approval_reject_ends() -> None:
    graph = _build_graph()
    reject_state = {"approval_response": _FakeApproval("reject")}
    approve_state = {"approval_response": _FakeApproval("approve")}
    assert graph._route_after_await_approval(reject_state) == END
    assert graph._route_after_await_approval(approve_state) == "execute_attack"


def test_route_after_evaluate_partial_routes_mutate() -> None:
    graph = _build_graph()
    assert graph._route_after_evaluate({"last_verdict": "PARTIAL"}) == "mutate"


def test_route_after_evaluate_success_confidence_threshold() -> None:
    graph = _build_graph()
    high = {"last_verdict": "SUCCESS", "verdict_row": SimpleNamespace(confidence=0.9)}
    low = {"last_verdict": "SUCCESS", "verdict_row": SimpleNamespace(confidence=0.5)}
    assert graph._route_after_evaluate(high) == "document"
    assert graph._route_after_evaluate(low) == "orchestrate"


def test_route_after_document_critical_requires_gate() -> None:
    graph = _build_graph()
    critical = {"report": SimpleNamespace(severity="CRITICAL")}
    high = {"report": SimpleNamespace(severity="HIGH")}
    assert graph._route_after_document(critical) == "await_critical_approval"
    assert graph._route_after_document(high) == "orchestrate"


@pytest.mark.asyncio
async def test_execute_attack_rejects_in_permissions_mode_without_calling_target() -> None:
    graph = _build_graph()
    graph.red_team = SimpleNamespace(execute_attack=None, generate_sequence=None)
    state = {
        "directive": SimpleNamespace(
            execution_mode="permissions",
            mutation_depth=2,
            model_copy=lambda update: None,
        ),
        "attack_sequence": [{"role": "user", "content": "x"}],
        "approval_response": _FakeApproval("reject"),
    }

    result = await graph.execute_attack(state)
    assert result["done"] is True


@pytest.mark.asyncio
async def test_execute_attack_uses_edited_sequence() -> None:
    async def _exec(seq, _path):
        assert seq == [{"role": "user", "content": "edited"}]
        return 200, "ok"

    graph = _build_graph()
    graph.red_team = SimpleNamespace(execute_attack=_exec, generate_sequence=None)
    state = {
        "directive": SimpleNamespace(
            execution_mode="permissions",
            mutation_depth=2,
            model_copy=lambda update: None,
            campaign_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            seed_case_ids=["T01-001"],
            target_category="prompt_injection",
            technique_ids=["ATLAS.T0051"],
            connection_path="copilot_endpoint",
            testing_mode="blackbox",
        ),
        "token_cost_usd": 0.1,
        "attack_sequence": [{"role": "user", "content": "original"}],
        "approval_response": _FakeApproval(
            "edit_approve", edited_sequence=[{"role": "user", "content": "edited"}]
        ),
    }

    result = await graph.execute_attack(state)
    assert result["attack_record"]["response_status_code"] == 200
    assert result["attack_record"]["target_response"] == "ok"
