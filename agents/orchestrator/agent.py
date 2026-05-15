from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agents.logger import get_logger
from agents.orchestrator.prioritizer import CoveragePrioritizer
from orchestration.messages import RegressionFlag
from orchestration.redis_queue import consume, publish
from state.models.attack import AttackRecord
from state.models.coverage import CoverageMap


class OrchestratorAgent:
    def __init__(self) -> None:
        self.log = get_logger("orchestrator")
        self.engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.prioritizer = CoveragePrioritizer()

        self.reassess_interval_seconds = 1800
        self.pause_seconds_on_cap = 3600
        self._last_reassess_at: datetime | None = None
        self._high_risk = {"CRITICAL", "HIGH"}

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.llm_client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1") if api_key else None
        self.llm_model = "anthropic/claude-sonnet-4-5"

        prompt_path = Path(__file__).parent / "prompts" / "orchestrator_system.txt"
        self.system_prompt = prompt_path.read_text(encoding="utf-8")
        self.log.info(
            "initialized reassess_interval=%ds llm_model=%s",
            self.reassess_interval_seconds,
            self.llm_model,
        )

    async def run_loop(self) -> None:
        self.log.info("run loop started")
        while True:
            await self._reassess_priorities_if_needed(force=False)

            async with self.session_maker() as db:
                directive = await self.prioritizer.next_directive(db, session_id=self._new_session_id())

            if directive is None:
                self.log.warning("no directive available, pausing %ds", self.pause_seconds_on_cap)
                await asyncio.sleep(self.pause_seconds_on_cap)
                continue

            self.log.info(
                "published directive category=%s session_id=%s",
                directive.target_category,
                directive.session_id,
            )
            await publish(directive)

            try:
                msg_id, message = await asyncio.wait_for(self._next_orchestrator_message(), timeout=1.0)
                if isinstance(message, RegressionFlag):
                    await self._handle_regression_flag(message)
                if message.target_agent == "broadcast":
                    await self._reassess_priorities_if_needed(force=True)
                _ = msg_id
            except TimeoutError:
                pass

    async def _next_orchestrator_message(self) -> tuple[str, Any]:
        stream = consume("orchestrator", block_ms=1000)
        return await anext(stream)

    async def _handle_regression_flag(self, message: RegressionFlag) -> None:
        self.log.warning("regression flag received attack_id=%s", message.attack_id)
        async with self.session_maker() as db:
            attack = await db.get(AttackRecord, UUID(str(message.attack_id)))
            if attack is None:
                return

            coverage = (
                await db.execute(
                    select(CoverageMap).where(CoverageMap.attack_category == attack.attack_category)
                )
            ).scalar_one_or_none()
            if coverage is None:
                return

            recently_patched = bool(
                coverage.last_patched_at
                and (datetime.now(timezone.utc) - coverage.last_patched_at).days <= 30
            )
            if recently_patched and str(coverage.residual_risk).upper() in self._high_risk:
                # Placeholder for alerting integration; keep state drift explicit.
                coverage.residual_risk = "CRITICAL"
                await db.commit()
                self.log.warning(
                    "residual_risk escalated to CRITICAL category=%s attack_id=%s",
                    attack.attack_category,
                    message.attack_id,
                )

    async def _reassess_priorities_if_needed(self, force: bool) -> None:
        self.log.debug("checking priority reassessment force=%s", force)
        now = datetime.now(timezone.utc)
        if not force and self._last_reassess_at is not None:
            delta = (now - self._last_reassess_at).total_seconds()
            if delta < self.reassess_interval_seconds:
                return

        async with self.session_maker() as db:
            coverage_rows = (await db.execute(select(CoverageMap))).scalars().all()
            if not coverage_rows:
                self._last_reassess_at = now
                return

            snapshot = [
                {
                    "attack_category": row.attack_category,
                    "residual_risk": row.residual_risk,
                    "total_attacks": row.total_attacks,
                    "success_count": row.success_count,
                    "partial_count": row.partial_count,
                    "failure_count": row.failure_count,
                }
                for row in coverage_rows
            ]

            reassessed = await self._llm_reassess(snapshot)
            if reassessed:
                for row in coverage_rows:
                    new_risk = reassessed.get(row.attack_category)
                    if new_risk in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
                        row.residual_risk = new_risk
                await db.commit()
                self.log.info("priorities updated: %s", reassessed)
            else:
                self.log.debug("no priority changes from reassessment")

        self._last_reassess_at = now

    async def _llm_reassess(self, snapshot: list[dict[str, Any]]) -> dict[str, str]:
        if self.llm_client is None:
            return {}

        completion = self.llm_client.chat.completions.create(
            model=self.llm_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": json.dumps({"coverage_snapshot": snapshot})},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        parsed = json.loads(content)
        categories = [c for c in parsed.get("priority_order", []) if isinstance(c, str)]

        mapping: dict[str, str] = {}
        for idx, category in enumerate(categories):
            if idx <= 1:
                mapping[category] = "CRITICAL"
            elif idx <= 3:
                mapping[category] = "HIGH"
            elif idx == 4:
                mapping[category] = "MEDIUM"
            else:
                mapping[category] = "LOW"
        return mapping

    def _new_session_id(self) -> UUID:
        return uuid4()
