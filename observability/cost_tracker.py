from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from state.models.event import AgentEvent

RATES_USD_PER_1K_TOKENS = {
    "mistralai/mistral-7b-instruct": {"input": 0.00025, "output": 0.00025},
    "openai/gpt-4o": {"input": 0.0025, "output": 0.01},
    "anthropic/claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
}


class CostTracker:
    def calculate(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rates = RATES_USD_PER_1K_TOKENS.get(model)
        if rates is None:
            raise ValueError(f"Unsupported model for cost tracking: {model}")

        input_cost = (input_tokens / 1000.0) * rates["input"]
        output_cost = (output_tokens / 1000.0) * rates["output"]
        return round(input_cost + output_cost, 8)

    async def record(
        self,
        db: AsyncSession,
        agent: str,
        model: str,
        session_id: UUID,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        cost = self.calculate(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        event = AgentEvent(
            session_id=session_id,
            agent=agent,
            event_type="token_usage",
            payload={
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
            cost_delta_usd=cost,
        )
        db.add(event)
        await db.commit()
        return cost

    async def session_total(self, db: AsyncSession, session_id: UUID) -> float:
        result = await db.execute(
            select(func.sum(AgentEvent.cost_delta_usd)).where(AgentEvent.session_id == session_id)
        )
        return float(result.scalar_one_or_none() or 0.0)

    async def daily_total(self, db: AsyncSession, agent: str | None = None) -> float:
        today = datetime.now(timezone.utc).date()
        stmt = select(func.sum(AgentEvent.cost_delta_usd)).where(
            func.date(AgentEvent.created_at) == today
        )
        if agent:
            stmt = stmt.where(AgentEvent.agent == agent)
        result = await db.execute(stmt)
        return float(result.scalar_one_or_none() or 0.0)
