from __future__ import annotations

import os
import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.websocket import publish_session_event
from state.db import get_db
from state.models.attack import AttackRecord
from state.models.verdict import Verdict

router = APIRouter(tags=["attacks"])


class ManualFireRequest(BaseModel):
    message: str
    surface: str = "chat"
    use_rag: bool = True
    session_id: uuid.UUID | None = None


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


@router.post("/manual-fire")
async def manual_fire(payload: ManualFireRequest) -> dict:
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

    return {"status_code": int(response.status_code), "response": response_body}


@router.get("/target-endpoint")
async def get_target_endpoint() -> dict:
    return {"target_endpoint": os.getenv("TARGET_ENDPOINT", "")}
