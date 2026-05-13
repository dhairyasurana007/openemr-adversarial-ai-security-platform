from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from orchestration.messages import (
    AttackResult,
    CampaignDirective,
    Escalation,
    HumanApprovalRequest,
    HumanApprovalResponse,
)
from orchestration.redis_queue import consume, publish
from state.models.attack import AttackRecord
from state.models.campaign import Campaign

from agents.red_team.mutator import Mutator

MODEL_PRIMARY = "mistralai/mistral-7b-instruct"
MODEL_FALLBACK = "anthropic/claude-sonnet-4-5"

MODEL_COST_PER_1K_TOKENS_USD = {
    MODEL_PRIMARY: 0.0003,
    MODEL_FALLBACK: 0.003,
}


class RedTeamAgent:
    def __init__(self) -> None:
        self.openrouter_api_key = os.environ["OPENROUTER_API_KEY"]
        self.target_base_url = os.environ["TARGET_BASE_URL"].rstrip("/")
        self.session_cookie = os.environ["SESSION_COOKIE"]
        self.csrf_token = os.environ["CSRF_TOKEN"]
        self.session_patient_uuid = os.environ["SESSION_PATIENT_UUID"]
        self.victim_uuid = os.environ["VICTIM_UUID"]
        self.internal_secret = os.getenv("CLINICAL_COPILOT_INTERNAL_SECRET")

        self.client = OpenAI(
            api_key=self.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.mutator = Mutator()

        self.engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

        prompt_dir = Path(__file__).parent / "prompts"
        self.attack_system_prompt = (prompt_dir / "attack_system.txt").read_text(encoding="utf-8")
        self.variant_system_prompt = (prompt_dir / "variant_system.txt").read_text(encoding="utf-8")

    async def run_loop(self) -> None:
        async for _, msg in consume("red_team"):
            if msg.message_type != "CAMPAIGN_DIRECTIVE":
                continue
            await self.handle_directive(msg)

    async def handle_directive(self, directive: CampaignDirective) -> AttackRecord | None:
        sequence, token_cost_usd = self.generate_sequence(directive)

        async with self.session_maker() as session:
            campaign = await session.get(Campaign, UUID(str(directive.campaign_id)))
            if campaign is None:
                raise ValueError(f"Campaign not found: {directive.campaign_id}")

            campaign.cost_so_far_usd = float(campaign.cost_so_far_usd) + token_cost_usd
            if campaign.cost_so_far_usd >= float(campaign.cost_cap_usd):
                campaign.status = "failed"
                await session.commit()
                await publish(
                    Escalation(
                        source_agent="red_team",
                        target_agent="orchestrator",
                        session_id=directive.session_id,
                        attack_id=UUID(int=0),
                        reason="campaign cost cap reached",
                    )
                )
                return None
            await session.commit()

        attack_id = uuid4()

        if directive.execution_mode == "permissions":
            approval = await self.wait_for_approval(directive, attack_id, sequence)
            if approval is None or approval.decision == "reject":
                return None
            if approval.decision == "edit_approve" and approval.edited_sequence:
                sequence = approval.edited_sequence
            if approval.decision == "escalate_mutation":
                directive = directive.model_copy(update={"mutation_depth": directive.mutation_depth + 1})
                sequence, _ = self.generate_sequence(directive)

        status_code, target_response = await self.execute_attack(sequence, directive.connection_path)

        async with self.session_maker() as session:
            attack_row = AttackRecord(
                id=attack_id,
                campaign_id=UUID(str(directive.campaign_id)),
                session_id=UUID(str(directive.session_id)),
                threat_id=directive.seed_case_ids[0].split("-")[0] if directive.seed_case_ids else "UNKNOWN",
                attack_category=directive.target_category,
                technique_id=directive.technique_ids[0] if directive.technique_ids else None,
                prompt_sequence=sequence,
                target_response=target_response,
                response_status_code=status_code,
                connection_path=directive.connection_path,
                testing_mode=directive.testing_mode,
                token_cost_usd=token_cost_usd,
                executed_at=datetime.now(timezone.utc),
                is_variant=False,
                parent_attack_id=None,
            )
            session.add(attack_row)
            await session.commit()
            await session.refresh(attack_row)

        await publish(
            AttackResult(
                source_agent="red_team",
                target_agent="judge",
                session_id=directive.session_id,
                attack_id=attack_row.id,
                campaign_id=directive.campaign_id,
                threat_id=attack_row.threat_id,
                prompt_sequence=sequence,
                target_response=target_response,
                response_status_code=status_code,
                token_cost_usd=token_cost_usd,
            )
        )

        return attack_row

    def generate_sequence(self, directive: CampaignDirective) -> tuple[list[dict[str, str]], float]:
        seed_context = self._load_seed_cases(directive.seed_case_ids)
        model = MODEL_FALLBACK if directive.mutation_depth > 3 else MODEL_PRIMARY

        payload = {
            "target_category": directive.target_category,
            "technique_ids": directive.technique_ids,
            "seed_cases": seed_context,
            "mutation_depth": directive.mutation_depth,
            "testing_mode": directive.testing_mode,
            "execution_mode": directive.execution_mode,
            "victim_uuid": self.victim_uuid,
            "session_patient_uuid": self.session_patient_uuid,
        }

        completion = self.client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.attack_system_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        parsed = json.loads(content)
        sequence = parsed.get("prompt_sequence")
        if not isinstance(sequence, list) or not sequence:
            raise ValueError("Model did not return prompt_sequence")

        total_tokens = int(getattr(completion.usage, "total_tokens", 0) or 0)
        cost = (total_tokens / 1000.0) * MODEL_COST_PER_1K_TOKENS_USD[model]
        return sequence, cost

    async def wait_for_approval(
        self,
        directive: CampaignDirective,
        attack_id: UUID,
        sequence: list[dict[str, str]],
        timeout_seconds: int = 1800,
    ) -> HumanApprovalResponse | None:
        await publish(
            HumanApprovalRequest(
                source_agent="red_team",
                target_agent="human",
                session_id=directive.session_id,
                attack_id=attack_id,
                campaign_id=directive.campaign_id,
                proposed_sequence=sequence,
                technique_id=directive.technique_ids[0] if directive.technique_ids else "unknown",
                target_category=directive.target_category,
                severity_estimate="HIGH",
            )
        )

        stream = consume("red_team", block_ms=1000)
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_seconds
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return None
            try:
                _, message = await asyncio.wait_for(stream.__anext__(), timeout=remaining)
            except (StopAsyncIteration, asyncio.TimeoutError):
                return None
            if message.message_type != "HUMAN_APPROVAL_RESPONSE":
                continue
            if UUID(str(message.attack_id)) != attack_id:
                continue
            return message

    async def execute_attack(
        self,
        prompt_sequence: list[dict[str, str]],
        connection_path: str,
    ) -> tuple[int, str]:
        endpoint = "/api/clinical-copilot/chat" if connection_path == "copilot_endpoint" else "/internal/eval"
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": self.csrf_token,
            "Cookie": self.session_cookie,
        }
        if self.internal_secret and connection_path == "fastapi_direct":
            headers["X-Clinical-Copilot-Internal-Secret"] = self.internal_secret

        payload = {
            "messages": prompt_sequence,
            "patient_uuid": self.session_patient_uuid,
            "target_patient_uuid": self.victim_uuid,
        }

        async with httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            proxy=os.getenv("HTTPS_PROXY", "http://proxy:8888"),
        ) as client:
            response = await client.post(f"{self.target_base_url}{endpoint}", headers=headers, json=payload)
        return int(response.status_code), response.text

    def _load_seed_cases(self, seed_case_ids: list[str]) -> list[dict[str, Any]]:
        seed_dir = Path(__file__).parents[2] / "evals" / "seed"
        id_set = set(seed_case_ids)
        found: list[dict[str, Any]] = []
        for yaml_file in sorted(seed_dir.glob("*.yaml")):
            import yaml

            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            for case in data.get("cases", []):
                if case.get("id") in id_set:
                    found.append(case)
        return found
