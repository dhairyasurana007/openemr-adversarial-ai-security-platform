from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.websocket import publish_session_event
from orchestration.messages import AttackResult
from orchestration.redis_queue import publish
from state.db import get_db
from state.models.attack import AttackRecord
from state.models.campaign import Campaign
from state.models.event import AgentEvent
from state.models.verdict import Verdict

router = APIRouter(tags=["attacks"])


class ManualFireRequest(BaseModel):
    message: str
    surface: str = "chat"
    use_rag: bool = True
    session_id: uuid.UUID | None = None
    testing_mode: str = "blackbox"
    attack_category: str = "prompt_injection"


@router.get("")
async def list_attacks(
    db: Annotated[AsyncSession, Depends(get_db)],
    campaign_id: uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
) -> list[dict]:
    stmt = select(AttackRecord)
    if campaign_id:
        stmt = stmt.where(AttackRecord.campaign_id == campaign_id)
    if category:
        stmt = stmt.where(AttackRecord.attack_category == category)
    if verdict:
        stmt = stmt.join(Verdict, Verdict.attack_id == AttackRecord.id).where(
            Verdict.verdict == verdict
        )

    rows = (await db.execute(stmt.order_by(AttackRecord.executed_at.desc()))).scalars().all()
    return [
        {
            "id": str(r.id),
            "campaign_id": str(r.campaign_id),
            "attack_category": r.attack_category,
        }
        for r in rows
    ]


@router.get("/{attack_id}")
async def get_attack(attack_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    row = await db.get(AttackRecord, attack_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Attack not found")
    return {
        "id": str(row.id),
        "campaign_id": str(row.campaign_id),
        "threat_id": row.threat_id,
        "attack_category": row.attack_category,
        "prompt_sequence": row.prompt_sequence,
        "target_response": row.target_response,
        "response_status_code": row.response_status_code,
    }


async def _get_or_create_manual_campaign(
    db: AsyncSession,
    session_id: uuid.UUID,
    testing_mode: str,
    target_category: str,
    target_url: str,
) -> Campaign:
    """Return the existing manual campaign for this session, or create one."""
    result = await db.execute(
        select(Campaign).where(Campaign.session_id == session_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        campaign = Campaign(
            id=uuid.uuid4(),
            session_id=session_id,
            execution_mode="auto",
            testing_mode=testing_mode,
            target_category=target_category,
            target_url=target_url,
            cost_cap_usd=0.0,
            mutation_depth=1,
            concurrency=1,
            status="active",
            cost_so_far_usd=0.0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(campaign)
        await db.flush()
    return campaign


@router.post("/manual-fire")
async def manual_fire(
    payload: ManualFireRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    target_endpoint = os.getenv("TARGET_ENDPOINT")
    if not target_endpoint:
        raise HTTPException(status_code=500, detail="TARGET_ENDPOINT is not configured")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    secret = os.getenv("CLINICAL_COPILOT_INTERNAL_SECRET")
    if secret:
        headers["X-Clinical-Copilot-Internal-Secret"] = secret

    body = {
        "message": payload.message,
        "surface": payload.surface,
        "use_rag": payload.use_rag,
    }

    if payload.session_id is not None:
        await publish_session_event(
            payload.session_id,
            {
                "event_type": "target_http.request",
                "payload": {
                    "method": "POST",
                    "url": target_endpoint,
                    "request_body": body,
                    "connection_path": "manual",
                },
            },
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(target_endpoint, headers=headers, json=body)

    try:
        response_body: object = response.json()
    except ValueError:
        response_body = response.text

    response_text = response.text

    if payload.session_id is not None:
        await publish_session_event(
            payload.session_id,
            {
                "event_type": "target_http.response",
                "payload": {
                    "method": "POST",
                    "url": target_endpoint,
                    "status": int(response.status_code),
                    "response_body": response_body,
                    "connection_path": "manual",
                },
            },
        )

        # Write an AttackRecord and notify the Judge so it evaluates this interaction.
        campaign = await _get_or_create_manual_campaign(
            db=db,
            session_id=payload.session_id,
            testing_mode=payload.testing_mode,
            target_category=payload.attack_category,
            target_url=target_endpoint,
        )
        attack_id = uuid.uuid4()
        prompt_sequence = [{"role": "user", "content": payload.message}]
        attack_record = AttackRecord(
            id=attack_id,
            campaign_id=campaign.id,
            session_id=payload.session_id,
            threat_id="MANUAL-INTERACTION",
            attack_category=payload.attack_category,
            technique_id=None,
            prompt_sequence=prompt_sequence,
            target_response=response_text,
            response_status_code=int(response.status_code),
            connection_path="manual",
            testing_mode=payload.testing_mode,
            token_cost_usd=0.0,
            executed_at=datetime.now(timezone.utc),
            is_variant=False,
            parent_attack_id=None,
        )
        db.add(attack_record)
        await db.commit()

    return {"status_code": int(response.status_code), "response": response_body}


class FinalizeSessionRequest(BaseModel):
    session_id: uuid.UUID


@router.post("/finalize-session")
async def finalize_session(
    payload: FinalizeSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Queue all un-evaluated AttackRecords for this session through the Judge."""
    already_evaluated = select(Verdict.attack_id)
    stmt = (
        select(AttackRecord)
        .where(AttackRecord.session_id == payload.session_id)
        .where(~AttackRecord.id.in_(already_evaluated))
    )
    records = (await db.execute(stmt)).scalars().all()
    total = len(records)

    db.add(AgentEvent(
        session_id=payload.session_id,
        agent="system",
        event_type="session.finalized",
        payload={"total_attacks": total},
        cost_delta_usd=0.0,
    ))
    await db.commit()
    await publish_session_event(
        payload.session_id,
        {"event_type": "session.finalized", "payload": {"total_attacks": total}},
    )

    for record in records:
        await publish(
            AttackResult(
                source_agent="red_team",
                target_agent="judge",
                session_id=record.session_id,
                campaign_id=record.campaign_id,
                attack_id=record.id,
                threat_id=record.threat_id,
                prompt_sequence=record.prompt_sequence,
                target_response=record.target_response,
                response_status_code=record.response_status_code,
                token_cost_usd=record.token_cost_usd,
            )
        )

    return {"queued": total}


@router.get("/target-endpoint")
async def get_target_endpoint() -> dict:
    return {"target_endpoint": os.getenv("TARGET_ENDPOINT", "")}
