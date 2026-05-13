from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from observability.cost_tracker import CostTracker
from observability.queries import (
    agent_activity_log,
    cost_dashboard,
    coverage_map,
    open_findings,
    regression_history,
    uncertain_queue,
    verdict_trends,
)
from state.models.event import AgentEvent


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@dataclass
class _CoverageRow:
    attack_category: str
    threat_model_ref: str
    total_attacks: int
    success_count: int
    partial_count: int
    failure_count: int
    residual_risk: str
    last_tested_at: datetime | None = None
    last_patched_at: datetime | None = None


class _FakeSession:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.coverage_rows = [
            _CoverageRow("prompt_injection", "THREAT_MODEL.md#3", 10, 2, 1, 7, "HIGH"),
            _CoverageRow("data_exfiltration", "THREAT_MODEL.md#4", 3, 0, 0, 3, "CRITICAL"),
        ]
        self.vuln_rows = [
            SimpleNamespace(
                id=uuid4(),
                severity="HIGH",
                status="DRAFT",
                attack_category="prompt_injection",
                clinical_impact="unsafe",
                filed_at=None,
            ),
            SimpleNamespace(
                id=uuid4(),
                severity="LOW",
                status="VALIDATED",
                attack_category="dos_cost",
                clinical_impact="none",
                filed_at=None,
            ),
        ]
        self.trend_rows = [SimpleNamespace(day=now - timedelta(days=1), verdict="FAILURE", count=2)]
        self.regression_rows = [
            SimpleNamespace(
                id=uuid4(),
                run_at=now,
                total_count=4,
                passed_count=3,
                failed_count=1,
                regressed_count=1,
            )
        ]
        self.event_rows = [
            SimpleNamespace(
                id=uuid4(),
                session_id=uuid4(),
                agent="judge",
                event_type="token_usage",
                payload={"model": "openai/gpt-4o"},
                cost_delta_usd=1.25,
                created_at=now,
            )
        ]
        self.uncertain_rows = [
            SimpleNamespace(
                id=uuid4(),
                attack_id=uuid4(),
                confidence=0.42,
                evidence_excerpt="disagreement",
                evaluated_at=now,
            )
        ]
        self.added = []
        self.commit_count = 0

    async def execute(self, query):
        q = str(query)
        if "FROM coverage_map" in q:
            return _ScalarsResult(self.coverage_rows)
        if "FROM vulnerability_reports" in q:
            rows = [r for r in self.vuln_rows if r.status in {"DRAFT", "FILED"}]
            if "severity" in q and "HIGH" in q:
                rows = [r for r in rows if r.severity == "HIGH"]
            return _ScalarsResult(rows)
        if "FROM verdicts" in q and "count" in q:
            return _RowsResult(self.trend_rows)
        if "FROM verdicts" in q:
            return _ScalarsResult(self.uncertain_rows)
        if "FROM regression_run" in q:
            return _ScalarsResult(self.regression_rows)
        if "FROM agent_events" in q and "GROUP BY" in q:
            return _RowsResult([SimpleNamespace(agent="judge", cost_usd=1.25)])
        if "FROM agent_events" in q and "sum(agent_events.cost_delta_usd)" in q:
            return _ScalarResult(2.5)
        if "FROM agent_events" in q:
            return _ScalarsResult(self.event_rows)
        return _RowsResult([])

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        self.commit_count += 1


@pytest.mark.asyncio
async def test_observability_queries_smoke():
    db = _FakeSession()

    coverage = await coverage_map(db)
    assert coverage[0]["attack_category"] == "data_exfiltration"

    findings = await open_findings(db, severity="HIGH")
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"

    trends = await verdict_trends(db, days=30)
    assert trends[0]["verdict"] == "FAILURE"

    history = await regression_history(db, limit=20)
    assert history[0]["failed"] == 1

    events = await agent_activity_log(db)
    assert events[0]["agent"] == "judge"

    costs = await cost_dashboard(db, days=30)
    assert costs["total_cost_usd"] == pytest.approx(1.25)

    uncertain = await uncertain_queue(db)
    assert uncertain[0]["confidence"] == pytest.approx(0.42)


def test_cost_tracker_calculate_and_unknown_model():
    tracker = CostTracker()
    cost = tracker.calculate("openai/gpt-4o", input_tokens=1000, output_tokens=500)
    assert 0.007 < cost < 0.009

    with pytest.raises(ValueError):
        tracker.calculate("unknown/model", input_tokens=1, output_tokens=1)


@pytest.mark.asyncio
async def test_cost_tracker_record_and_totals():
    db = _FakeSession()
    tracker = CostTracker()

    session_id = uuid4()
    cost = await tracker.record(
        db,
        agent="judge",
        model="openai/gpt-4o",
        session_id=session_id,
        input_tokens=1000,
        output_tokens=1000,
    )

    assert cost == pytest.approx(0.0125)
    assert db.commit_count == 1
    assert isinstance(db.added[0], AgentEvent)

    session_total = await tracker.session_total(db, session_id)
    daily_total_all = await tracker.daily_total(db)
    daily_total_agent = await tracker.daily_total(db, agent="judge")

    assert session_total == pytest.approx(2.5)
    assert daily_total_all == pytest.approx(2.5)
    assert daily_total_agent == pytest.approx(2.5)
