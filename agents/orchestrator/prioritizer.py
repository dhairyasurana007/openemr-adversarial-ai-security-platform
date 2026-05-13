from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from orchestration.messages import CampaignDirective
from state.models.coverage import CoverageMap
from state.models.event import AgentEvent


class CoveragePrioritizer:
    RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    RISK_WEIGHTS = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def __init__(self) -> None:
        self.daily_cost_cap_usd = float(os.getenv("DAILY_COST_CAP_USD", "50.00"))
        self.session_cost_cap_usd = float(os.getenv("SESSION_COST_CAP_USD", "5.00"))

    async def score(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Returns attack categories sorted by priority score (descending).
        Score = residual_risk_weight * (1 - coverage_ratio) * recency_penalty
        residual_risk_weight: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1
        coverage_ratio: success_count / max(total_attacks, 1)
        recency_penalty: 1.0 if never tested, decays by 0.1 per day since last_tested
        """
        result = await db.execute(select(CoverageMap))
        now = datetime.now(timezone.utc)
        scored: list[dict[str, Any]] = []

        for row in result.scalars().all():
            risk = (row.residual_risk or "MEDIUM").upper()
            risk_weight = self.RISK_WEIGHTS.get(risk, self.RISK_WEIGHTS["MEDIUM"])
            coverage_ratio = row.success_count / max(row.total_attacks, 1)

            if row.last_tested_at is None:
                recency_penalty = 1.0
            else:
                last_tested = row.last_tested_at
                if last_tested.tzinfo is None:
                    last_tested = last_tested.replace(tzinfo=timezone.utc)
                days_since = max((now - last_tested).days, 0)
                recency_penalty = max(0.1, 1.0 - (days_since * 0.1))

            score = risk_weight * (1 - coverage_ratio) * recency_penalty
            scored.append(
                {
                    "attack_category": row.attack_category,
                    "residual_risk": risk,
                    "coverage_ratio": coverage_ratio,
                    "recency_penalty": recency_penalty,
                    "score": score,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored

    async def next_directive(
        self, db: AsyncSession, session_id: uuid.UUID
    ) -> CampaignDirective | None:
        """
        1. Check daily cost from AgentEvent table; if >= DAILY_COST_CAP_USD, return None.
        2. Run score() to pick top-priority category.
        3. Query taxonomy_techniques for top-10 technique_ids in that category when available.
        4. Query AttackCase seed IDs for that category from evals/seed loader.
        5. Build and return CampaignDirective.
        """
        daily_cost_query = select(func.coalesce(func.sum(AgentEvent.cost_delta_usd), 0.0)).where(
            AgentEvent.created_at >= func.date_trunc("day", func.now())
        )
        daily_cost = float((await db.execute(daily_cost_query)).scalar_one())
        if daily_cost >= self.daily_cost_cap_usd:
            return None

        priorities = await self.score(db)
        if not priorities:
            return None

        top_category = priorities[0]["attack_category"]
        technique_ids = await self._load_technique_ids(db, top_category)
        seed_case_ids = self._load_seed_case_ids(top_category)

        return CampaignDirective(
            source_agent="orchestrator",
            target_agent="red_team",
            session_id=session_id,
            campaign_id=uuid.uuid4(),
            target_category=top_category,
            technique_ids=technique_ids[:10],
            seed_case_ids=seed_case_ids,
            mutation_depth=2,
            cost_cap_usd=self.session_cost_cap_usd,
            testing_mode="blackbox",
            execution_mode="auto",
            connection_path="copilot_endpoint",
            cost_so_far=daily_cost,
        )

    async def _load_technique_ids(self, db: AsyncSession, category: str) -> list[str]:
        """Best-effort taxonomy lookup with deterministic fallback from THREAT_MODEL IDs."""
        try:
            queries = [
                text(
                    "SELECT id FROM taxonomy_techniques "
                    "WHERE category = :category "
                    "ORDER BY severity_prior DESC "
                    "LIMIT 10"
                ),
                text(
                    "SELECT id FROM taxonomy_techniques "
                    "WHERE attack_category = :category "
                    "ORDER BY severity_prior DESC "
                    "LIMIT 10"
                ),
            ]
            rows = []
            for query in queries:
                try:
                    rows = (await db.execute(query, {"category": category})).all()
                except Exception:
                    rows = []
                if rows:
                    break
            ids = [str(row[0]) for row in rows]
            if ids:
                return ids
        except Exception:
            pass

        return self._extract_atlas_ids_from_threat_model(category)

    def _load_seed_case_ids(self, category: str) -> list[str]:
        seed_dir = Path(__file__).resolve().parents[2] / "evals" / "seed"
        wanted = category.lower()
        case_ids: list[str] = []

        for seed_file in sorted(seed_dir.glob("*.yaml")):
            data = yaml.safe_load(seed_file.read_text(encoding="utf-8"))
            meta_category = str(data.get("meta", {}).get("category", "")).strip().lower()
            normalized_meta = meta_category.replace(" ", "_")
            if normalized_meta != wanted:
                continue
            for case in data.get("cases", []):
                case_id = case.get("id")
                if case_id:
                    case_ids.append(str(case_id))

        return case_ids

    def _extract_atlas_ids_from_threat_model(self, category: str) -> list[str]:
        threat_model_path = Path(__file__).resolve().parents[2] / "THREAT_MODEL.md"
        if not threat_model_path.exists():
            return []

        content = threat_model_path.read_text(encoding="utf-8")
        category_headers = {
            "prompt_injection": "## 3",
            "data_exfiltration": "## 4",
            "state_corruption": "## 5",
            "tool_misuse": "## 6",
            "dos_cost": "## 7",
            "identity_trust": "## 8",
        }
        start_marker = category_headers.get(category)
        if start_marker is None:
            return []

        start = content.find(start_marker)
        if start < 0:
            return []

        next_section = content.find("\n## ", start + len(start_marker))
        section = content[start:] if next_section < 0 else content[start:next_section]

        ids: list[str] = []
        seen: set[str] = set()
        for match in re.findall(r"ATLAS\.T\d{4}", section):
            if match not in seen:
                ids.append(match)
                seen.add(match)
        return ids[:10]
