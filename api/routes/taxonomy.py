from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthUser, require_operator
from state.db import get_db
from state.models.taxonomy import TaxonomyTechnique
from taxonomy.refresh import TaxonomyRefresher

router = APIRouter(tags=["taxonomy"])


@router.get("/techniques")
async def list_techniques(
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
) -> list[dict]:
    stmt = select(TaxonomyTechnique)
    if category:
        stmt = stmt.where(TaxonomyTechnique.category == category)
    if source:
        stmt = stmt.where(TaxonomyTechnique.source == source)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "source": r.source,
            "category": r.category,
            "name": r.name,
            "severity_prior": r.severity_prior,
            "deprecated": r.deprecated,
        }
        for r in rows
    ]


@router.post("/refresh")
async def refresh_taxonomy(user: Annotated[AuthUser, Depends(require_operator)]) -> dict:
    summary = await TaxonomyRefresher().refresh()
    return {"status": "ok", "summary": summary}
