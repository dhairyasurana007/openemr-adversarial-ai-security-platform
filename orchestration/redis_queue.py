from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from orchestration.messages import (
    AttackApprovalRequest,
    AttackApprovalResponse,
    AttackResult,
    BaseMessage,
    CampaignDirective,
    Escalation,
    HumanApprovalResponse,
    JudgeVerdict,
    RegressionFlag,
)

_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        redis_url = os.environ["REDIS_URL"]
        _client = aioredis.from_url(redis_url, decode_responses=True)
    return _client


async def publish(msg: BaseMessage) -> None:
    """Write typed message to the stream for target_agent."""
    redis_client = await get_redis()
    stream = f"agentforge:{msg.target_agent}"
    await redis_client.xadd(stream, {"payload": msg.model_dump_json()})


async def consume(
    agent_name: str,
    block_ms: int = 5000,
) -> AsyncGenerator[tuple[str, BaseMessage], None]:
    """Yield (message_id, parsed_message) from the agent's stream."""
    type_map = {
        "CAMPAIGN_DIRECTIVE": CampaignDirective,
        "ATTACK_RESULT": AttackResult,
        "JUDGE_VERDICT": JudgeVerdict,
        "HUMAN_APPROVAL_RESPONSE": HumanApprovalResponse,
        "ATTACK_APPROVAL_REQUEST": AttackApprovalRequest,
        "ATTACK_APPROVAL_RESPONSE": AttackApprovalResponse,
        "ESCALATION": Escalation,
        "REGRESSION_FLAG": RegressionFlag,
    }

    redis_client = await get_redis()
    stream = f"agentforge:{agent_name}"
    last_id = "0-0"

    while True:
        entries = await redis_client.xread({stream: last_id}, block=block_ms, count=10)
        if not entries:
            continue

        for _, messages in entries:
            for msg_id, fields in messages:
                raw = json.loads(fields["payload"])
                model_cls = type_map.get(raw["message_type"])
                if model_cls is not None:
                    yield msg_id, model_cls.model_validate(raw)
                last_id = msg_id


async def ack(agent_name: str, msg_id: str) -> None:
    redis_client = await get_redis()
    await redis_client.xdel(f"agentforge:{agent_name}", msg_id)
