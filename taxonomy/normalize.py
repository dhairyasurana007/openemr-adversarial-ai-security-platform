from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field


class TechniqueRecord(BaseModel):
    id: str
    source: Literal["atlas", "garak", "harmbench", "jailbreakbench", "healthcare"]
    atlas_tactic: str
    category: str
    name: str
    description: str
    technique_pattern: str
    mutation_strategies: list[str]
    healthcare_relevance: str
    severity_prior: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    threat_model_ref: str | None = None
    copilot_trust_zone: str | None = None
    last_ingested: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: str
    deprecated: bool = False
    fingerprint: str


def compute_fingerprint(technique_id: str, description: str) -> str:
    return sha256(f"{technique_id}{description}".encode("utf-8")).hexdigest()
