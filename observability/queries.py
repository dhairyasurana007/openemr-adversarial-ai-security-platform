from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from state.models.coverage import CoverageMap
from state.models.event import AgentEvent
from state.models.regression import RegressionRun
from state.models.verdict import Verdict
from state.models.vulnerability import VulnerabilityReport

_RISK_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


async def coverage_map(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(CoverageMap))
    rows = result.scalars().all()
    ordered = sorted(rows, key=lambda r: (_RISK_ORDER.get(r.residual_risk, 99), r.attack_category))
    return [
        {
            "attack_category": row.attack_category,
            "threat_model_ref": row.threat_model_ref,
            "total_attacks": row.total_attacks,
            "success_count": row.success_count,
            "partial_count": row.partial_count,
            "failure_count": row.failure_count,
            "residual_risk": row.residual_risk,
            "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
            "last_patched_at": row.last_patched_at.isoformat() if row.last_patched_at else None,
        }
        for row in ordered
    ]


async def open_findings(db: AsyncSession, severity: str | None = None) -> list[dict]:
    stmt = select(VulnerabilityReport).where(VulnerabilityReport.status.in_(["DRAFT", "FILED"]))
    if severity:
        stmt = stmt.where(VulnerabilityReport.severity == severity)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "severity": row.severity,
            "status": row.status,
            "attack_category": row.attack_category,
            "clinical_impact": row.clinical_impact,
            "filed_at": row.filed_at.isoformat() if row.filed_at else None,
        }
        for row in rows
    ]


async def verdict_trends(db: AsyncSession, days: int = 30) -> list[dict]:
    day_bucket = func.date_trunc("day", Verdict.evaluated_at).label("day")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(day_bucket, Verdict.verdict, func.count().label("count"))
        .where(Verdict.evaluated_at >= cutoff)
        .group_by(day_bucket, Verdict.verdict)
        .order_by(day_bucket.asc(), Verdict.verdict.asc())
    )
    result = await db.execute(stmt)
    return [
        {
            "day": row.day.isoformat() if row.day else None,
            "verdict": row.verdict,
            "count": row.count,
        }
        for row in result.all()
    ]


async def regression_history(db: AsyncSession, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(RegressionRun).order_by(RegressionRun.run_at.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "run_at": row.run_at.isoformat() if row.run_at else None,
            "total": row.total_count,
            "passed": row.passed_count,
            "failed": row.failed_count,
            "regressed": row.regressed_count,
        }
        for row in rows
    ]


async def agent_activity_log(db: AsyncSession, session_id: UUID | None = None) -> list[dict]:
    stmt = select(AgentEvent).order_by(AgentEvent.created_at.desc())
    if session_id:
        stmt = stmt.where(AgentEvent.session_id == session_id)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "session_id": str(row.session_id),
            "agent": row.agent,
            "event_type": row.event_type,
            "payload": row.payload,
            "cost_delta_usd": row.cost_delta_usd,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


async def cost_dashboard(db: AsyncSession, days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(AgentEvent.agent, func.sum(AgentEvent.cost_delta_usd).label("cost_usd"))
        .where(AgentEvent.created_at >= cutoff)
        .group_by(AgentEvent.agent)
        .order_by(func.sum(AgentEvent.cost_delta_usd).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    by_agent = [{"agent": row.agent, "cost_usd": float(row.cost_usd or 0.0)} for row in rows]
    total = sum(item["cost_usd"] for item in by_agent)
    return {"days": days, "total_cost_usd": total, "by_agent": by_agent}


async def uncertain_queue(db: AsyncSession) -> list[dict]:
    stmt = (
        select(Verdict)
        .where(Verdict.verdict == "UNCERTAIN")
        .where(Verdict.evaluator_user_id.is_(None))
        .order_by(Verdict.evaluated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "attack_id": str(row.attack_id),
            "confidence": row.confidence,
            "evidence_excerpt": row.evidence_excerpt,
            "evaluated_at": row.evaluated_at.isoformat() if row.evaluated_at else None,
        }
        for row in rows
    ]
