from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthUser, require_operator
from regression.harness import RegressionHarness
from state.db import get_db

router = APIRouter(tags=["regression"])


@router.get("/history")
async def get_regression_history(db: Annotated[AsyncSession, Depends(get_db)]) -> list[dict]:
    from observability.queries import regression_history

    return await regression_history(db)


@router.post("/trigger")
async def trigger_regression(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_operator)],
) -> dict:
    result = await RegressionHarness().run_suite(db)
    return {"status": "completed", "summary": result}
