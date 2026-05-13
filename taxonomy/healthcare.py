from __future__ import annotations

import json
import os

import httpx
from openai import OpenAI

from taxonomy.normalize import TechniqueRecord, compute_fingerprint

HHS_BREACH_URL = (
    "https://www.hhs.gov/hipaa/for-professionals/breach-notification/breach-reporting/index.html"
)


class HealthcareIngestor:
    source = "healthcare"
    model = "anthropic/claude-sonnet-4-5"

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )

    async def ingest(self) -> list[TechniqueRecord]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(HHS_BREACH_URL)
            response.raise_for_status()
        return self.from_breach_text(response.text)

    def from_breach_text(self, breach_text: str) -> list[TechniqueRecord]:
        prompt = (
            "Given this healthcare data breach report, identify any patterns related to "
            "AI/LLM system vulnerabilities. Output JSON array of "
            "{pattern_name, attack_type, clinical_impact, atlas_tactic}."
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": breach_text[:12000]},
            ],
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        patterns = data.get("patterns", data if isinstance(data, list) else [])
        if not isinstance(patterns, list):
            return []

        records: list[TechniqueRecord] = []
        for idx, pattern in enumerate(patterns, start=1):
            if not isinstance(pattern, dict):
                continue
            name = str(pattern.get("pattern_name", f"Healthcare pattern {idx}")).strip()
            attack_type = str(pattern.get("attack_type", "prompt_injection")).strip()
            clinical_impact = str(pattern.get("clinical_impact", "Clinical safety impact")).strip()
            tactic = str(pattern.get("atlas_tactic", "Execution")).strip()
            category = self._to_category(attack_type, tactic)
            technique_id = f"HEALTH.{idx:04d}"
            description = f"{name}: {clinical_impact}"
            records.append(
                TechniqueRecord(
                    id=technique_id,
                    source="healthcare",
                    atlas_tactic=tactic,
                    category=category,
                    name=name,
                    description=description,
                    technique_pattern=attack_type,
                    mutation_strategies=["healthcare_context_swap", "multi_turn_variation"],
                    healthcare_relevance=clinical_impact,
                    severity_prior="CRITICAL",
                    source_url=HHS_BREACH_URL,
                    fingerprint=compute_fingerprint(technique_id, description),
                )
            )
        return records

    def _to_category(self, attack_type: str, tactic: str) -> str:
        text = f"{attack_type} {tactic}".lower()
        if "exfil" in text or "leak" in text:
            return "data_exfiltration"
        if "identity" in text or "auth" in text:
            return "identity_trust"
        if "tool" in text:
            return "tool_misuse"
        if "state" in text:
            return "state_corruption"
        if "cost" in text or "dos" in text:
            return "dos_cost"
        return "prompt_injection"
