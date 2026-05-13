from __future__ import annotations

import csv
from io import StringIO

import httpx

from taxonomy.normalize import TechniqueRecord, compute_fingerprint

HARMBENCH_URL = (
    "https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/data/"
    "behavior_datasets/harmbench_behaviors_text_all.csv"
)


class HarmBenchIngestor:
    source = "harmbench"

    async def ingest(self) -> list[TechniqueRecord]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(HARMBENCH_URL)
            response.raise_for_status()
        return self.parse_csv(response.text)

    def parse_csv(self, csv_text: str) -> list[TechniqueRecord]:
        rows = csv.DictReader(StringIO(csv_text))
        records: list[TechniqueRecord] = []
        for row in rows:
            behavior_id = str(row.get("BehaviorID", "")).strip()
            behavior = str(row.get("Behavior", "")).strip()
            category = self._map_category(str(row.get("Category", "")))
            if not behavior_id or not behavior:
                continue
            technique_id = f"HARMBENCH.{behavior_id}"
            records.append(
                TechniqueRecord(
                    id=technique_id,
                    source="harmbench",
                    atlas_tactic="Execution",
                    category=category,
                    name=behavior[:80],
                    description=behavior,
                    technique_pattern=behavior,
                    mutation_strategies=["gcg", "autodan", "pair", "multi_turn_variation"],
                    healthcare_relevance=(
                        "General adversarial behavior pattern applicable to copilots"
                    ),
                    severity_prior="HIGH",
                    source_url=HARMBENCH_URL,
                    fingerprint=compute_fingerprint(technique_id, behavior),
                )
            )
        return records

    def _map_category(self, category: str) -> str:
        lowered = category.lower()
        if "privacy" in lowered or "data" in lowered:
            return "data_exfiltration"
        if "fraud" in lowered or "identity" in lowered:
            return "identity_trust"
        if "misuse" in lowered:
            return "tool_misuse"
        return "prompt_injection"
