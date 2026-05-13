from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from state.db import get_db
from state.models.attack import AttackRecord
from state.models.verdict import Verdict

router = APIRouter(tags=["attacks"])


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
