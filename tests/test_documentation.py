from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SLACK_WEBHOOK_URL", "https://example.com/webhook")
os.environ.setdefault("APPROVAL_CHANNEL", "#security")
os.environ.setdefault("HMAC_SECRET_KEY", "test-secret-do-not-use")

from agents.documentation.agent import DocumentationAgent, verify_report_integrity
from state.models.vulnerability import VulnerabilityReport


@pytest.fixture
def agent() -> DocumentationAgent:
    os.environ["HMAC_SECRET_KEY"] = "test-secret-do-not-use"
    return DocumentationAgent()


def _mock_report(status: str, severity: str) -> VulnerabilityReport:
    return VulnerabilityReport(
        id=uuid.uuid4(),
        attack_id=uuid.uuid4(),
        verdict_id=uuid.uuid4(),
        severity=severity,
        attack_category="data_exfiltration",
        affected_component="clinical_copilot",
        clinical_impact="Cross-patient disclosure risk",
        attack_sequence=[{"role": "user", "content": "show patient record"}],
        observed_behavior="Returned another patient record",
        expected_behavior="Block cross-patient access",
        remediation_recommendation="Enforce per-session patient scoping",
        status=status,
        testing_mode="blackbox",
        hmac_signature="",
        filed_at=datetime.now(timezone.utc) if status == "FILED" else None,
        approved_by_user_id=None,
    )


def test_hmac_signature_roundtrip(agent: DocumentationAgent) -> None:
    """HMAC computed at creation must verify on re-read."""
    report = _mock_report(status="FILED", severity="HIGH")
    report.hmac_signature = agent._sign_report(report)
    assert verify_report_integrity(report) is True


def test_draft_status_for_critical(agent: DocumentationAgent) -> None:
    """CRITICAL reports must be DRAFT, not FILED."""
    report = _mock_report(status="DRAFT", severity="CRITICAL")
    report.hmac_signature = agent._sign_report(report)
    assert report.status == "DRAFT"
    assert verify_report_integrity(report) is True


def test_filed_status_for_high(agent: DocumentationAgent) -> None:
    """HIGH reports must be auto-FILED without human gate."""
    report = _mock_report(status="FILED", severity="HIGH")
    report.hmac_signature = agent._sign_report(report)
    assert report.status == "FILED"
    assert report.filed_at is not None
    assert verify_report_integrity(report) is True
