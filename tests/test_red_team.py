from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "mock")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("TARGET_BASE_URL", "http://localhost:8080")
os.environ.setdefault("SESSION_COOKIE", "PHPSESSID=test")
os.environ.setdefault("CSRF_TOKEN", "test_csrf")
os.environ.setdefault("SESSION_PATIENT_UUID", "aaaaaaaa-0000-0000-0000-000000000001")
os.environ.setdefault("VICTIM_UUID", "bbbbbbbb-0000-0000-0000-000000000002")

from agents.red_team.agent import MODEL_FALLBACK, MODEL_PRIMARY, RedTeamAgent
from agents.red_team.mutator import Mutator
from agents.red_team.proxy import MITMPROXY_AVAILABLE
from orchestration.messages import CampaignDirective, HumanApprovalResponse


class _FakeCompletion:
    def __init__(self, sequence: list[dict[str, str]], total_tokens: int = 1000):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=str({"prompt_sequence": sequence}).replace("'", '"')))]
        self.usage = SimpleNamespace(total_tokens=total_tokens)


class _FakeClient:
    def __init__(self) -> None:
        self.seen_models: list[str] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.seen_models.append(kwargs["model"])
        return _FakeCompletion([{"role": "user", "content": "attack"}], total_tokens=2000)


def _directive(depth: int = 2) -> CampaignDirective:
    return CampaignDirective(
        source_agent="orchestrator",
        target_agent="red_team",
        session_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        target_category="prompt_injection",
        technique_ids=["ATLAS.T0051"],
        seed_case_ids=["T01-001"],
        mutation_depth=depth,
        cost_cap_usd=1.0,
        testing_mode="blackbox",
        execution_mode="auto",
        connection_path="copilot_endpoint",
    )


def test_generate_sequence_prefers_primary_model_for_low_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = RedTeamAgent()
    fake_client = _FakeClient()
    monkeypatch.setattr(agent, "client", fake_client)
    monkeypatch.setattr(agent, "_load_seed_cases", lambda _: [{"id": "T01-001"}])

    sequence, _ = agent.generate_sequence(_directive(depth=2))

    assert sequence
    assert fake_client.seen_models[-1] == MODEL_PRIMARY


def test_generate_sequence_uses_fallback_model_for_high_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = RedTeamAgent()
    fake_client = _FakeClient()
    monkeypatch.setattr(agent, "client", fake_client)
    monkeypatch.setattr(agent, "_load_seed_cases", lambda _: [{"id": "T01-001"}])

    sequence, _ = agent.generate_sequence(_directive(depth=4))

    assert sequence
    assert fake_client.seen_models[-1] == MODEL_FALLBACK


@pytest.mark.asyncio
async def test_wait_for_approval_timeout_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = RedTeamAgent()
    directive = _directive()
    attack_id = uuid.uuid4()

    async def _fake_publish(_msg):
        return None

    async def _fake_consume(_agent_name: str, block_ms: int = 5000):
        if False:
            yield

    monkeypatch.setattr("agents.red_team.agent.publish", _fake_publish)
    monkeypatch.setattr("agents.red_team.agent.consume", _fake_consume)

    result = await agent.wait_for_approval(directive, attack_id, [{"role": "user", "content": "x"}], timeout_seconds=1)
    assert result is None


@pytest.mark.asyncio
async def test_wait_for_approval_returns_matching_response(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = RedTeamAgent()
    directive = _directive()
    attack_id = uuid.uuid4()

    async def _fake_publish(_msg):
        return None

    async def _fake_consume(_agent_name: str, block_ms: int = 5000):
        yield "1-0", HumanApprovalResponse(
            source_agent="human",
            target_agent="red_team",
            session_id=directive.session_id,
            attack_id=attack_id,
            decision="approve",
            edited_sequence=None,
            operator_user_id=uuid.uuid4(),
        )

    monkeypatch.setattr("agents.red_team.agent.publish", _fake_publish)
    monkeypatch.setattr("agents.red_team.agent.consume", _fake_consume)

    result = await agent.wait_for_approval(directive, attack_id, [{"role": "user", "content": "x"}], timeout_seconds=2)
    assert result is not None
    assert result.decision == "approve"


def test_mutator_returns_attackcase_variants() -> None:
    from evals.schemas import AttackCase, TargetRequest

    mutator = Mutator()
    case = AttackCase(
        id="T01-001",
        title="base",
        description="desc",
        target=TargetRequest(endpoint="/x", method="POST", body={"q": "test"}),
    )

    variants = mutator.mutate(case, "prompt_injection", partial_evidence="blocked")
    assert variants
    assert all(v.id.startswith("T01-001-v") for v in variants)


def test_proxy_module_import_guard() -> None:
    assert isinstance(MITMPROXY_AVAILABLE, bool)
