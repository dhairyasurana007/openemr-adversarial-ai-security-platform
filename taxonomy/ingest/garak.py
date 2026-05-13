from __future__ import annotations

from typing import Any

from taxonomy.normalize import TechniqueRecord, compute_fingerprint


def _sanitize_description(text: str) -> str:
    lines = text.splitlines()
    clean: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('"') or "jailbreak" in stripped.lower():
            continue
        clean.append(stripped)
    return " ".join(clean).strip()


def _tag_to_category(tags: list[str]) -> str:
    lowered = " ".join(tags).lower()
    if "exfil" in lowered or "leak" in lowered:
        return "data_exfiltration"
    if "tool" in lowered:
        return "tool_misuse"
    if "identity" in lowered or "auth" in lowered:
        return "identity_trust"
    if "state" in lowered:
        return "state_corruption"
    if "cost" in lowered or "dos" in lowered:
        return "dos_cost"
    return "prompt_injection"


class GarakIngestor:
    source = "garak"
    source_url = "https://github.com/NVIDIA/garak"

    async def ingest(self) -> list[TechniqueRecord]:
        try:
            from garak.probes import base as garak_base  # type: ignore
        except Exception:
            return []

        probe_classes: list[type[Any]] = []
        for obj in vars(garak_base).values():
            if isinstance(obj, type) and hasattr(obj, "__name__"):
                probe_classes.append(obj)

        return self.from_probe_classes(probe_classes)

    def from_probe_classes(self, probe_classes: list[type[Any]]) -> list[TechniqueRecord]:
        records: list[TechniqueRecord] = []
        for cls in probe_classes:
            if cls.__name__.startswith("_"):
                continue
            raw_description = str(
                getattr(cls, "description", "") or getattr(cls, "__doc__", "") or ""
            )
            description = _sanitize_description(raw_description)
            name = str(getattr(cls, "name", cls.__name__))
            tags = [str(t) for t in getattr(cls, "tags", [])]
            category = _tag_to_category(tags)
            technique_id = f"GARAK.{cls.__name__.upper()}"
            records.append(
                TechniqueRecord(
                    id=technique_id,
                    source="garak",
                    atlas_tactic="Execution",
                    category=category,
                    name=name,
                    description=description or name,
                    technique_pattern=name,
                    mutation_strategies=["semantic_rephrasing", "persona_injection"],
                    healthcare_relevance="Can expose unsafe model behavior in clinical contexts",
                    severity_prior="HIGH",
                    source_url=self.source_url,
                    fingerprint=compute_fingerprint(technique_id, description or name),
                )
            )
        return records
