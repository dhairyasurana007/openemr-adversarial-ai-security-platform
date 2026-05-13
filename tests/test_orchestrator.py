from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agents.orchestrator.prioritizer import CoveragePrioritizer


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _CoverageResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


@dataclass
class _CoverageRow:
    attack_category: str
    residual_risk: str
    total_attacks: int
    success_count: int
    partial_count: int
    failure_count: int
    last_tested_at: datetime | None = None


class _FakeSession:
    def __init__(self, daily_cost: float, coverage_rows: list[_CoverageRow], technique_rows=None):
        self.daily_cost = daily_cost
        self.coverage_rows = coverage_rows
        self.technique_rows = technique_rows or []

    async def execute(self, query, params=None):
        query_text = str(query)
        if "sum(agent_events.cost_delta_usd)" in query_text:
            return _ScalarResult(self.daily_cost)
        if "FROM taxonomy_techniques" in query_text:
            return _RowsResult(self.technique_rows)
        return _CoverageResult(self.coverage_rows)


@pytest.mark.asyncio
async def test_score_prioritizes_higher_risk_and_lower_coverage() -> None:
    prioritizer = CoveragePrioritizer()
    rows = [
        _CoverageRow(
            attack_category="prompt_injection",
            residual_risk="HIGH",
            total_attacks=10,
            success_count=9,
            partial_count=0,
            failure_count=1,
            last_tested_at=datetime.now(timezone.utc),
        ),
        _CoverageRow(
            attack_category="data_exfiltration",
            residual_risk="CRITICAL",
            total_attacks=2,
            success_count=0,
            partial_count=0,
            failure_count=2,
            last_tested_at=None,
        ),
    ]

    session = _FakeSession(daily_cost=0.0, coverage_rows=rows)
    ranked = await prioritizer.score(session)

    assert ranked[0]["attack_category"] == "data_exfiltration"
    assert ranked[0]["score"] > ranked[1]["score"]


@pytest.mark.asyncio
async def test_score_applies_recency_decay_floor() -> None:
    prioritizer = CoveragePrioritizer()
    very_old = datetime.now(timezone.utc) - timedelta(days=20)
    rows = [
        _CoverageRow(
            attack_category="dos_cost",
            residual_risk="MEDIUM",
            total_attacks=1,
            success_count=0,
            partial_count=0,
            failure_count=1,
            last_tested_at=very_old,
        )
    ]

    session = _FakeSession(daily_cost=0.0, coverage_rows=rows)
    ranked = await prioritizer.score(session)

    assert ranked[0]["recency_penalty"] == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_next_directive_returns_none_when_daily_cap_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAILY_COST_CAP_USD", "10.0")
    prioritizer = CoveragePrioritizer()
    rows = [
        _CoverageRow(
            attack_category="prompt_injection",
            residual_risk="HIGH",
            total_attacks=0,
            success_count=0,
            partial_count=0,
            failure_count=0,
        )
    ]

    session = _FakeSession(daily_cost=10.0, coverage_rows=rows)
    directive = await prioritizer.next_directive(session, session_id=uuid4())

    assert directive is None


@pytest.mark.asyncio
async def test_next_directive_builds_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSION_COST_CAP_USD", "7.5")
    prioritizer = CoveragePrioritizer()
    rows = [
        _CoverageRow(
            attack_category="prompt_injection",
            residual_risk="CRITICAL",
            total_attacks=0,
            success_count=0,
            partial_count=0,
            failure_count=0,
        )
    ]
    technique_rows = [("ATLAS.T0051",), ("ATLAS.T0052",)]
    session = _FakeSession(daily_cost=3.25, coverage_rows=rows, technique_rows=technique_rows)

    monkeypatch.setattr(
        prioritizer,
        "_load_seed_case_ids",
        lambda category: ["T01-001", "T01-002"] if category == "prompt_injection" else [],
    )

    directive = await prioritizer.next_directive(session, session_id=uuid4())

    assert directive is not None
    assert directive.target_category == "prompt_injection"
    assert directive.technique_ids == ["ATLAS.T0051", "ATLAS.T0052"]
    assert directive.seed_case_ids == ["T01-001", "T01-002"]
    assert directive.cost_cap_usd == pytest.approx(7.5)
    assert directive.cost_so_far == pytest.approx(3.25)
