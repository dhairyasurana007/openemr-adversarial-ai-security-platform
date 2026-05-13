from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from observability.queries import (
    agent_activity_log,
    cost_dashboard,
    coverage_map,
    open_findings,
    uncertain_queue,
    verdict_trends,
)
from state.db import get_db

router = APIRouter(tags=["observability"])


@router.get("/coverage")
async def get_coverage(db: Annotated[AsyncSession, Depends(get_db)]) -> list[dict]:
    return await coverage_map(db)


@router.get("/findings")
async def get_findings(
    db: Annotated[AsyncSession, Depends(get_db)], severity: str | None = Query(default=None)
) -> list[dict]:
    return await open_findings(db, severity=severity)


@router.get("/trends")
async def get_trends(
    db: Annotated[AsyncSession, Depends(get_db)], days: int = Query(default=30, ge=1, le=365)
) -> list[dict]:
    return await verdict_trends(db, days=days)


@router.get("/cost")
async def get_cost(
    db: Annotated[AsyncSession, Depends(get_db)], days: int = Query(default=30, ge=1, le=365)
) -> dict:
    return await cost_dashboard(db, days=days)


@router.get("/uncertain")
async def get_uncertain(db: Annotated[AsyncSession, Depends(get_db)]) -> list[dict]:
    return await uncertain_queue(db)


@router.get("/agent-log")
async def get_agent_log(
    db: Annotated[AsyncSession, Depends(get_db)], session_id: UUID | None = Query(default=None)
) -> list[dict]:
    return await agent_activity_log(db, session_id=session_id)
