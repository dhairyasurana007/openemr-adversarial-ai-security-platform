from __future__ import annotations

import uuid

import pytest

from orchestration.messages import CampaignDirective
from orchestration.queue import ack, consume, get_redis, publish


@pytest.mark.asyncio
async def test_publish_consume_roundtrip() -> None:
    stream = "agentforge:red_team"
    redis_client = await get_redis()
    await redis_client.delete(stream)

    session_id = uuid.uuid4()
    msg = CampaignDirective(
        source_agent="orchestrator",
        target_agent="red_team",
        session_id=session_id,
        campaign_id=uuid.uuid4(),
        target_category="prompt_injection",
        technique_ids=["ATLAS.T0051"],
        seed_case_ids=["T01-001"],
        mutation_depth=2,
        cost_cap_usd=1.0,
        testing_mode="blackbox",
        execution_mode="auto",
        connection_path="copilot_endpoint",
    )

    await publish(msg)

    async for msg_id, received in consume("red_team", block_ms=1000):
        if received.session_id == session_id:
            await ack("red_team", msg_id)
            break
    else:
        raise AssertionError("No message consumed from redis stream")

    remaining = await redis_client.xlen(stream)
    assert remaining == 0
