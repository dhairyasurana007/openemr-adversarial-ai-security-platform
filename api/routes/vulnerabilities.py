from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthUser, require_ciso
from state.db import get_db
from state.models.vulnerability import VulnerabilityReport

router = APIRouter(tags=["vulnerabilities"])
HMAC_SECRET_KEY = os.environ.get("HMAC_SECRET_KEY", "")


class ReportApprovalRequest(BaseModel):
    decision: str


def _calc_report_hmac(report: VulnerabilityReport) -> str:
    payload = {
        "id": str(report.id),
        "attack_id": str(report.attack_id),
        "verdict_id": str(report.verdict_id),
        "severity": report.severity,
        "attack_category": report.attack_category,
        "status": report.status,
        "testing_mode": report.testing_mode,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(HMAC_SECRET_KEY.encode("utf-8"), body, hashlib.sha256).hexdigest()


@router.get("")
async def list_vulnerabilities(
    db: Annotated[AsyncSession, Depends(get_db)],
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[dict]:
    stmt = select(VulnerabilityReport)
    if severity:
        stmt = stmt.where(VulnerabilityReport.severity == severity)
    if status:
        stmt = stmt.where(VulnerabilityReport.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "severity": r.severity,
            "status": r.status,
            "attack_category": r.attack_category,
        }
        for r in rows
    ]


@router.get("/{report_id}")
async def get_vulnerability(
    report_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    row = await db.get(VulnerabilityReport, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Vulnerability report not found")

    integrity_ok = bool(HMAC_SECRET_KEY) and hmac.compare_digest(
        row.hmac_signature,
        _calc_report_hmac(row),
    )
    return {
        "id": str(row.id),
        "attack_id": str(row.attack_id),
        "severity": row.severity,
        "status": row.status,
        "attack_sequence": row.attack_sequence,
        "integrity_ok": integrity_ok,
    }


@router.patch("/{report_id}/approve")
async def approve_report(
    report_id: uuid.UUID,
    payload: ReportApprovalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_ciso)],
) -> dict:
    row = await db.get(VulnerabilityReport, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Vulnerability report not found")

    if payload.decision == "approve":
        row.status = "FILED"
        row.approved_by_user_id = user.id
    elif payload.decision == "reject":
        row.status = "DRAFT"
    else:
        raise HTTPException(status_code=400, detail="Decision must be approve or reject")

    await db.commit()
    return {"id": str(row.id), "status": row.status}
