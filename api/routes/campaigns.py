from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthUser, require_operator
from orchestration.messages import CampaignDirective
from orchestration.redis_queue import publish
from state.db import get_db
from state.models.campaign import Campaign

router = APIRouter(tags=["campaigns"])


class CampaignCreate(BaseModel):
    execution_mode: Literal["auto", "permissions"]
    testing_mode: Literal["whitebox", "blackbox"]
    target_category: str
    technique_ids: list[str] = Field(default_factory=list)
    seed_case_ids: list[str] = Field(default_factory=list)
    mutation_depth: int = 1
    cost_cap_usd: float = 5.0
    concurrency: int = 1
    target_url: str = "http://localhost"
    connection_path: Literal["copilot_endpoint", "fastapi_direct"] = "copilot_endpoint"


class CampaignModePatch(BaseModel):
    execution_mode: Literal["auto", "permissions"]


@router.post("")
async def create_campaign(
    payload: CampaignCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_operator)],
) -> dict:
    campaign = Campaign(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        execution_mode=payload.execution_mode,
        testing_mode=payload.testing_mode,
        target_category=payload.target_category,
        target_url=payload.target_url,
        cost_cap_usd=payload.cost_cap_usd,
        mutation_depth=payload.mutation_depth,
        concurrency=payload.concurrency,
        status="pending",
        cost_so_far_usd=0.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(campaign)
    await db.commit()

    await publish(
        CampaignDirective(
            source_agent="orchestrator",
            target_agent="red_team",
            session_id=campaign.session_id,
            campaign_id=campaign.id,
            target_category=campaign.target_category,
            technique_ids=payload.technique_ids,
            seed_case_ids=payload.seed_case_ids,
            mutation_depth=campaign.mutation_depth,
            cost_cap_usd=campaign.cost_cap_usd,
            testing_mode=campaign.testing_mode,
            execution_mode=campaign.execution_mode,
            connection_path=payload.connection_path,
        )
    )

    return {
        "id": str(campaign.id),
        "session_id": str(campaign.session_id),
        "status": campaign.status,
    }


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "id": str(campaign.id),
        "session_id": str(campaign.session_id),
        "execution_mode": campaign.execution_mode,
        "testing_mode": campaign.testing_mode,
        "target_category": campaign.target_category,
        "status": campaign.status,
        "cost_so_far_usd": campaign.cost_so_far_usd,
    }


@router.patch("/{campaign_id}/mode")
async def patch_campaign_mode(
    campaign_id: uuid.UUID,
    payload: CampaignModePatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_operator)],
) -> dict:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.execution_mode = payload.execution_mode
    await db.commit()
    return {"id": str(campaign.id), "execution_mode": campaign.execution_mode}
