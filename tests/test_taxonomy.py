from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("OPENROUTER_API_KEY", "mock")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")

from taxonomy.healthcare import HealthcareIngestor
from taxonomy.ingest.atlas import AtlasIngestor
from taxonomy.ingest.garak import GarakIngestor
from taxonomy.ingest.harmbench import HarmBenchIngestor
from taxonomy.ingest.jailbreakbench import JailbreakBenchIngestor
from taxonomy.normalize import TechniqueRecord, compute_fingerprint


def test_compute_fingerprint_is_deterministic() -> None:
    left = compute_fingerprint("ATLAS.T0051", "desc")
    right = compute_fingerprint("ATLAS.T0051", "desc")
    assert left == right
    assert len(left) == 64


def test_atlas_parse_maps_tactic_to_category() -> None:
    yaml_text = """
techniques:
  - id: ATLAS.T0051
    name: Prompt Injection
    description: Attack prompt chain.
    tactics: ["ML Attack Staging"]
"""
    records = AtlasIngestor().parse(yaml_text)
    assert records
    assert records[0].source == "atlas"
    assert records[0].category == "prompt_injection"
    assert records[0].id == "ATLAS.T0051"


def test_garak_description_sanitization_filters_literal_payloads() -> None:
    class Probe:
        __name__ = "PromptProbe"
        name = "PromptProbe"
        tags = ["prompt", "leak"]
        description = '"IGNORE PREVIOUS"\nnormal line\njailbreak payload text'

    records = GarakIngestor().from_probe_classes([Probe])
    assert records
    assert "IGNORE PREVIOUS" not in records[0].description
    assert "jailbreak" not in records[0].description.lower()
    assert records[0].category == "data_exfiltration"


def test_harmbench_parse_csv_builds_records() -> None:
    csv_text = "BehaviorID,Behavior,Category,Tags\n1,Steal patient data,Privacy,tag\n"
    records = HarmBenchIngestor().parse_csv(csv_text)
    assert len(records) == 1
    assert records[0].source == "harmbench"
    assert records[0].category == "data_exfiltration"


def test_jailbreakbench_parse_csv_builds_records() -> None:
    csv_text = "id,behavior\n10,Bypass constraints with roleplay\n"
    records = JailbreakBenchIngestor().parse_csv(csv_text)
    assert len(records) == 1
    assert records[0].source == "jailbreakbench"
    assert "persona_injection" in records[0].mutation_strategies


def test_healthcare_ingestor_transforms_llm_patterns(monkeypatch) -> None:
    class _FakeCompletions:
        @staticmethod
        def create(**_kwargs):
            content = (
                '{"patterns":[{"pattern_name":"Cross-patient disclosure",'
                '"attack_type":"data leak","clinical_impact":"Wrong patient exposure",'
                '"atlas_tactic":"Exfiltration"}]}'
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class _FakeClient:
        chat = SimpleNamespace(completions=_FakeCompletions())

    ingestor = HealthcareIngestor()
    monkeypatch.setattr(ingestor, "client", _FakeClient())

    records = ingestor.from_breach_text("sample breach text")
    assert len(records) == 1
    assert isinstance(records[0], TechniqueRecord)
    assert records[0].source == "healthcare"
    assert records[0].severity_prior == "CRITICAL"
    assert records[0].category == "data_exfiltration"
