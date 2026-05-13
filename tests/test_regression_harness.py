from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from regression.harness import RegressionHarness
from regression.reporter import RegressionReporter
from state.models.attack import AttackRecord
from state.models.regression import RegressionRun
from state.models.verdict import Verdict as VerdictRow


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _ScalarResult(self._rows)


@dataclass
class _CompletedProcess:
    stdout: str
    stderr: str
    returncode: int = 0


class _FakeSession:
    def __init__(self, attack: AttackRecord | None = None, verdict: VerdictRow | None = None):
        self.attack = attack
        self.verdict = verdict
        self.runs: list[RegressionRun] = []
        self.commits = 0

    async def get(self, model, key):
        if model is AttackRecord and self.attack and self.attack.id == key:
            return self.attack
        return None

    async def execute(self, query):
        query_text = str(query)
        if "FROM verdicts" in query_text:
            return _ExecuteResult([self.verdict] if self.verdict else [])
        if "FROM regression_run" in query_text:
            rows = sorted(
                self.runs,
                key=lambda r: r.run_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            return _ExecuteResult(rows)
        return _ExecuteResult([])

    def add(self, row):
        if isinstance(row, RegressionRun) and row.run_at is None:
            row.run_at = datetime.now(timezone.utc)
        self.runs.append(row)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_generate_test_writes_pytest_file():
    tmp_path = Path(".tmp_regression_test_1")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    attack_id = uuid4()
    attack = AttackRecord(
        id=attack_id,
        campaign_id=uuid4(),
        session_id=uuid4(),
        threat_id="T07",
        attack_category="data_exfiltration",
        technique_id="ATLAS.T0051",
        prompt_sequence=[{"role": "user", "content": "leak PHI"}],
        target_response="response",
        response_status_code=200,
        connection_path="copilot_endpoint",
        testing_mode="blackbox",
        token_cost_usd=0.1,
        executed_at=datetime.now(timezone.utc),
        is_variant=False,
        parent_attack_id=None,
    )
    verdict = VerdictRow(
        id=uuid4(),
        attack_id=attack_id,
        verdict="SUCCESS",
        confidence=0.95,
        evidence_excerpt="PHI disclosed",
        layer_triggered="rule_engine",
        model_a_verdict=None,
        model_b_verdict=None,
        regression_flag=False,
        rubric_version="1.0.0",
        evaluated_at=datetime.now(timezone.utc),
        evaluator_user_id=None,
    )
    session = _FakeSession(attack=attack, verdict=verdict)

    harness = RegressionHarness(suite_dir=tmp_path)
    path = await harness.generate_test(attack_id, session)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert f"Attack: {attack_id}" in content
    assert "def test_" in content
    assert "ATTACK_SEQUENCE" in content


@pytest.mark.asyncio
async def test_run_suite_persists_summary_and_publishes_flags(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_path = Path(".tmp_regression_test_2")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    attack_id = uuid4()
    session_id = uuid4()
    attack = AttackRecord(
        id=attack_id,
        campaign_id=uuid4(),
        session_id=session_id,
        threat_id="T01",
        attack_category="prompt_injection",
        technique_id=None,
        prompt_sequence=[{"role": "user", "content": "ignore rules"}],
        target_response="unsafe",
        response_status_code=200,
        connection_path="copilot_endpoint",
        testing_mode="blackbox",
        token_cost_usd=0.2,
        executed_at=datetime.now(timezone.utc),
        is_variant=False,
        parent_attack_id=None,
    )
    session = _FakeSession(attack=attack, verdict=None)

    test_path = tmp_path / f"test_{attack_id}.py"
    test_path.write_text("def test_placeholder():\n    assert False\n", encoding="utf-8")

    stdout = f"{test_path.as_posix()}::test_placeholder FAILED\n"
    monkeypatch.setattr(
        "regression.harness.subprocess.run",
        lambda *args, **kwargs: _CompletedProcess(stdout=stdout, stderr="", returncode=1),
    )

    published = []

    async def _fake_publish(msg):
        published.append(msg)

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setattr("orchestration.queue.publish", _fake_publish)

    harness = RegressionHarness(suite_dir=tmp_path)
    summary = await harness.run_suite(session)

    assert summary["total"] == 1
    assert summary["failed"] == 1
    assert summary["regressed"] == 1
    assert len(session.runs) == 1
    assert session.runs[0].failed_count == 1
    assert len(published) == 1
    assert str(published[0].attack_id) == str(attack_id)


@pytest.mark.asyncio
async def test_reporter_diff_identifies_new_failures_and_passes():
    session = _FakeSession()
    session.runs.extend(
        [
            RegressionRun(
                total_count=2,
                passed_count=1,
                failed_count=1,
                regressed_count=1,
                failed_tests=["regression/suite/test_a.py::test_a"],
                passed_tests=["regression/suite/test_b.py::test_b"],
                raw_output="",
                run_at=datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc),
            ),
            RegressionRun(
                total_count=2,
                passed_count=2,
                failed_count=0,
                regressed_count=0,
                failed_tests=[],
                passed_tests=[
                    "regression/suite/test_a.py::test_a",
                    "regression/suite/test_b.py::test_b",
                ],
                raw_output="",
                run_at=datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc),
            ),
        ]
    )

    reporter = RegressionReporter()
    diff = await reporter.diff_report(session)

    assert diff["newly_failed"] == ["regression/suite/test_a.py::test_a"]
    assert diff["newly_passed"] == []
    assert diff["current_failed"] == ["regression/suite/test_a.py::test_a"]
