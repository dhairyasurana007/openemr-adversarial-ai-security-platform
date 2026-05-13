from __future__ import annotations

import hmac
import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from orchestration.messages import AttackApprovalRequest, JudgeVerdict
from orchestration.redis_queue import consume, publish
from state.models.attack import AttackRecord
from state.models.verdict import Verdict
from state.models.vulnerability import VulnerabilityReport

CANONICAL_FIELDS = [
    "severity",
    "attack_category",
    "affected_component",
    "clinical_impact",
    "attack_sequence",
    "observed_behavior",
    "expected_behavior",
    "remediation_recommendation",
    "testing_mode",
    "status",
]


class DocumentationAgent:
    def __init__(self) -> None:
        self.openrouter_api_key = os.environ["OPENROUTER_API_KEY"]
        self.slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
        self.approval_channel = os.environ["APPROVAL_CHANNEL"]
        self.hmac_secret_key = os.environ["HMAC_SECRET_KEY"]

        self.client = OpenAI(
            api_key=self.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = "anthropic/claude-sonnet-4-5"

        self.engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

        base_dir = Path(__file__).parent
        self.docs_system_prompt = (base_dir / "prompts" / "docs_system.txt").read_text(encoding="utf-8")
        self.critical_template = (base_dir / "templates" / "critical.txt").read_text(encoding="utf-8")
        self.high_below_template = (
            base_dir / "templates" / "high_and_below.txt"
        ).read_text(encoding="utf-8")

    async def generate_report(self, verdict_msg: JudgeVerdict) -> VulnerabilityReport:
        attack_id = UUID(str(verdict_msg.attack_id))

        async with self.session_maker() as session:
            attack = await session.get(AttackRecord, attack_id)
            if attack is None:
                raise ValueError(f"AttackRecord not found for attack_id={attack_id}")

            verdict_row = await session.scalar(select(Verdict).where(Verdict.attack_id == attack_id))
            if verdict_row is None:
                raise ValueError(f"Verdict not found for attack_id={attack_id}")

        payload = {
            "attack_id": str(attack.id),
            "campaign_id": str(attack.campaign_id),
            "session_id": str(attack.session_id),
            "threat_id": attack.threat_id,
            "attack_category": attack.attack_category,
            "prompt_sequence": attack.prompt_sequence,
            "target_response": attack.target_response,
            "response_status_code": attack.response_status_code,
            "connection_path": attack.connection_path,
            "testing_mode": attack.testing_mode,
            "verdict": {
                "value": verdict_row.verdict,
                "confidence": verdict_row.confidence,
                "evidence_excerpt": verdict_row.evidence_excerpt,
                "layer_triggered": verdict_row.layer_triggered,
            },
        }

        llm_doc = self._generate_structured_doc(payload)

        severity = str(llm_doc["severity"]).upper()
        if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            severity = "MEDIUM"

        status = "DRAFT" if severity == "CRITICAL" else "FILED"

        report = VulnerabilityReport(
            attack_id=attack.id,
            verdict_id=verdict_row.id,
            severity=severity,
            attack_category=llm_doc["attack_category"],
            affected_component=llm_doc["affected_component"],
            clinical_impact=llm_doc["clinical_impact"],
            attack_sequence=llm_doc["attack_sequence"],
            observed_behavior=llm_doc["observed_behavior"],
            expected_behavior=llm_doc["expected_behavior"],
            remediation_recommendation=llm_doc["remediation_recommendation"],
            status=status,
            testing_mode=attack.testing_mode,
            hmac_signature="",
            filed_at=datetime.now(timezone.utc) if status == "FILED" else None,
            approved_by_user_id=None,
        )

        report.hmac_signature = self._sign_report(report)

        async with self.session_maker() as session:
            session.add(report)
            await session.commit()
            await session.refresh(report)

        if severity == "CRITICAL":
            await publish(
                AttackApprovalRequest(
                    source_agent="documentation",
                    target_agent="human",
                    session_id=attack.session_id,
                    vulnerability_id=report.id,
                )
            )
            await self._send_slack_notification(report)
        else:
            self._write_report_file(report)

        return report

    async def run_loop(self) -> None:
        async for _, message in consume("documentation"):
            if message.message_type != "JUDGE_VERDICT":
                continue
            if message.verdict != "SUCCESS" or message.confidence < 0.85:
                continue
            await self.generate_report(message)

    def _generate_structured_doc(self, payload: dict[str, Any]) -> dict[str, Any]:
        completion = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.docs_system_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)

        required = {
            "severity",
            "attack_category",
            "affected_component",
            "clinical_impact",
            "attack_sequence",
            "observed_behavior",
            "expected_behavior",
            "remediation_recommendation",
        }
        missing = required.difference(data)
        if missing:
            raise ValueError(f"Documentation model response missing fields: {sorted(missing)}")

        if not isinstance(data["attack_sequence"], list):
            raise ValueError("attack_sequence must be a list")

        return data

    def _sign_report(self, report: VulnerabilityReport) -> str:
        canonical = self._canonical_report_json(report)
        return hmac.new(self.hmac_secret_key.encode(), canonical.encode(), sha256).hexdigest()

    def _canonical_report_json(self, report: VulnerabilityReport) -> str:
        payload = {field: getattr(report, field) for field in CANONICAL_FIELDS}
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _write_report_file(self, report: VulnerabilityReport) -> None:
        out_dir = Path("vulnerability_reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{report.id}.json"
        out_path.write_text(
            json.dumps(
                {
                    "id": str(report.id),
                    "attack_id": str(report.attack_id),
                    "verdict_id": str(report.verdict_id),
                    "severity": report.severity,
                    "attack_category": report.attack_category,
                    "affected_component": report.affected_component,
                    "clinical_impact": report.clinical_impact,
                    "attack_sequence": report.attack_sequence,
                    "observed_behavior": report.observed_behavior,
                    "expected_behavior": report.expected_behavior,
                    "remediation_recommendation": report.remediation_recommendation,
                    "status": report.status,
                    "testing_mode": report.testing_mode,
                    "hmac_signature": report.hmac_signature,
                    "filed_at": report.filed_at.isoformat() if report.filed_at else None,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    async def _send_slack_notification(self, report: VulnerabilityReport) -> None:
        body = {
            "channel": self.approval_channel,
            "text": (
                f"[CRITICAL] Vulnerability requires approval: {report.id}\\n"
                f"Category: {report.attack_category}\\n"
                f"Impact: {report.clinical_impact}\\n"
                f"Link: /findings/{report.id}"
            ),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(self.slack_webhook_url, json=body)


def verify_report_integrity(report: VulnerabilityReport) -> bool:
    canonical = json.dumps(
        {field: getattr(report, field) for field in CANONICAL_FIELDS},
        sort_keys=True,
        separators=(",", ":"),
    )
    expected = hmac.new(os.environ["HMAC_SECRET_KEY"].encode(), canonical.encode(), sha256).hexdigest()
    return hmac.compare_digest(expected, report.hmac_signature)
