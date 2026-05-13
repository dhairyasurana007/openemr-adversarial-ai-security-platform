from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthUser, require_ciso, require_operator
from api.websocket import publish_session_event
from orchestration.messages import HumanApprovalResponse
from orchestration.redis_queue import publish
from state.db import get_db
from state.models.attack import AttackRecord
from state.models.vulnerability import VulnerabilityReport

router = APIRouter(tags=["approvals"])


class AttackApprovalDecision(BaseModel):
    decision: Literal["approve", "reject", "edit_approve", "escalate_mutation"]
    edited_sequence: list[dict] | None = None


class ReportApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]


@router.post("/attack/{attack_id}")
async def approve_attack(
    attack_id: uuid.UUID,
    payload: AttackApprovalDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_operator)],
) -> dict:
    attack = await db.get(AttackRecord, attack_id)
    if attack is None:
        raise HTTPException(status_code=404, detail="Attack not found")

    await publish(
        HumanApprovalResponse(
            source_agent="human",
            target_agent="red_team",
            session_id=attack.session_id,
            attack_id=attack.id,
            decision=payload.decision,
            edited_sequence=payload.edited_sequence,
            operator_user_id=user.id,
        )
    )
    await publish_session_event(
        attack.session_id,
        {
            "event": "attack_approval",
            "attack_id": str(attack.id),
            "decision": payload.decision,
        },
    )
    return {"attack_id": str(attack.id), "decision": payload.decision}


@router.post("/report/{report_id}")
async def approve_report(
    report_id: uuid.UUID,
    payload: ReportApprovalDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_ciso)],
) -> dict:
    report = await db.get(VulnerabilityReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Vulnerability report not found")

    if payload.decision == "approve":
        report.status = "FILED"
        report.approved_by_user_id = user.id
    else:
        report.status = "DRAFT"
    await db.commit()

    attack = await db.get(AttackRecord, report.attack_id)
    if attack is not None:
        await publish_session_event(
            attack.session_id,
            {
                "event": "report_approval",
                "report_id": str(report.id),
                "decision": payload.decision,
            },
        )

    return {"report_id": str(report.id), "status": report.status}
