from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthUser, require_operator
from state.db import get_db
from state.models.verdict import Verdict

router = APIRouter(tags=["verdicts"])


class ResolveVerdictRequest(BaseModel):
    final_verdict: str


@router.get("")
async def list_verdicts(
    db: Annotated[AsyncSession, Depends(get_db)],
    verdict: str | None = Query(default=None),
) -> list[dict]:
    stmt = select(Verdict)
    if verdict:
        stmt = stmt.where(Verdict.verdict == verdict)
    rows = (await db.execute(stmt.order_by(Verdict.evaluated_at.desc()))).scalars().all()
    return [{"id": str(v.id), "attack_id": str(v.attack_id), "verdict": v.verdict} for v in rows]


@router.patch("/{verdict_id}/resolve")
async def resolve_uncertain_verdict(
    verdict_id: uuid.UUID,
    payload: ResolveVerdictRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_operator)],
) -> dict:
    row = await db.get(Verdict, verdict_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Verdict not found")
    if row.verdict != "UNCERTAIN":
        raise HTTPException(status_code=400, detail="Only UNCERTAIN verdicts can be resolved")
    row.verdict = payload.final_verdict
    row.evaluator_user_id = user.id
    row.evaluated_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "id": str(row.id),
        "verdict": row.verdict,
        "evaluator_user_id": str(row.evaluator_user_id),
    }
