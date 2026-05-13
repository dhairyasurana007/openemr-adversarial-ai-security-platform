from __future__ import annotations

from typing import Any

import httpx
import yaml

from taxonomy.normalize import TechniqueRecord, compute_fingerprint

ATLAS_URL = "https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/dist/ATLAS.yaml"

TACTIC_TO_CATEGORY = {
    "ML Attack Staging": "prompt_injection",
    "ML Model Access": "identity_trust",
    "Reconnaissance": "identity_trust",
    "Exfiltration": "data_exfiltration",
    "Impact": "dos_cost",
    "Execution": "tool_misuse",
    "Privilege Escalation": "state_corruption",
    "Credential Access": "identity_trust",
    "Collection": "data_exfiltration",
}


class AtlasIngestor:
    source = "atlas"

    async def ingest(self) -> list[TechniqueRecord]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ATLAS_URL)
            response.raise_for_status()
        return self.parse(response.text)

    def parse(self, yaml_text: str) -> list[TechniqueRecord]:
        data = yaml.safe_load(yaml_text) or {}
        techniques = data.get("techniques", [])
        out: list[TechniqueRecord] = []
        for item in techniques:
            if not isinstance(item, dict):
                continue
            out.append(self._to_record(item))
        return out

    def _to_record(self, item: dict[str, Any]) -> TechniqueRecord:
        technique_id = str(item.get("id", "ATLAS.UNKNOWN"))
        name = str(item.get("name", technique_id))
        description = str(item.get("description", "")).strip()
        tactics = item.get("tactics") or []
        tactic = str(tactics[0] if tactics else "Execution")
        category = TACTIC_TO_CATEGORY.get(tactic, "prompt_injection")
        impact = str(item.get("impact", "")).lower()
        severity = "CRITICAL" if "high" in impact else "HIGH"

        return TechniqueRecord(
            id=technique_id,
            source="atlas",
            atlas_tactic=tactic,
            category=category,
            name=name,
            description=description,
            technique_pattern=description or name,
            mutation_strategies=["semantic_rephrasing", "multi_turn_variation"],
            healthcare_relevance="Potential to undermine clinical safety controls",
            severity_prior=severity,
            threat_model_ref=None,
            copilot_trust_zone="copilot_endpoint",
            source_url=ATLAS_URL,
            fingerprint=compute_fingerprint(technique_id, description),
        )
