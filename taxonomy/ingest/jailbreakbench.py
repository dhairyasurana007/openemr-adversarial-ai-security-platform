from __future__ import annotations

import csv
from io import StringIO

import httpx

from taxonomy.normalize import TechniqueRecord, compute_fingerprint

JAILBREAKBENCH_URL = (
    "https://raw.githubusercontent.com/JailbreakBench/jailbreakbench/main/src/"
    "jailbreakbench/data/behaviors.csv"
)


class JailbreakBenchIngestor:
    source = "jailbreakbench"

    async def ingest(self) -> list[TechniqueRecord]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(JAILBREAKBENCH_URL)
            response.raise_for_status()
        return self.parse_csv(response.text)

    def parse_csv(self, csv_text: str) -> list[TechniqueRecord]:
        rows = csv.DictReader(StringIO(csv_text))
        records: list[TechniqueRecord] = []
        for row in rows:
            behavior = str(row.get("behavior", "") or row.get("Behavior", "")).strip()
            if not behavior:
                continue
            behavior_id = str(
                row.get("id", "") or row.get("behavior_id", "") or row.get("BehaviorID", "")
            ).strip()
            if not behavior_id:
                behavior_id = str(len(records) + 1)
            technique_id = f"JBB.{behavior_id}"
            records.append(
                TechniqueRecord(
                    id=technique_id,
                    source="jailbreakbench",
                    atlas_tactic="ML Attack Staging",
                    category="prompt_injection",
                    name=f"Jailbreak behavior {behavior_id}",
                    description=behavior,
                    technique_pattern="jailbreak prompt pattern",
                    mutation_strategies=[
                        "semantic_rephrasing",
                        "persona_injection",
                        "encoding_variation",
                    ],
                    healthcare_relevance=(
                        "Represents jailbreak pathways that can bypass safety prompts"
                    ),
                    severity_prior="HIGH",
                    source_url=JAILBREAKBENCH_URL,
                    fingerprint=compute_fingerprint(technique_id, behavior),
                )
            )
        return records
