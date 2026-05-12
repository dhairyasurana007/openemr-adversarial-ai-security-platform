"""
Pydantic schemas for adversarial test cases and execution results.

A CaseSuite is one YAML file (one threat category).
A CaseResult is produced by the runner for each case executed.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Exploitability(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Verdict(str, Enum):
    PASS = "pass"        # Attack failed — system defended correctly
    FAIL = "fail"        # Attack succeeded — vulnerability confirmed
    PARTIAL = "partial"  # Ambiguous; needs human review
    ERROR = "error"      # Test infrastructure / connectivity failure


class TargetRequest(BaseModel):
    """Describes the HTTP request the runner will send."""
    endpoint: str
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    # session_cookie | bearer_token | internal_secret | none
    auth_type: str = "session_cookie"
    timeout_seconds: int = 30


class DetectionRule(BaseModel):
    """A single machine-checkable criterion for evaluating a response."""
    # "response_contains" | "response_not_contains" | "status_code_is"
    # | "status_code_not" | "json_path_equals" | "llm_judge"
    kind: str
    value: Any
    description: str


class AttackCase(BaseModel):
    id: str
    title: str
    description: str
    target: TargetRequest
    preconditions: list[str] = Field(default_factory=list)
    expected_safe_behaviors: list[str] = Field(default_factory=list)
    # Machine-checkable rules; FAIL verdict if any "fail_if_*" rule matches
    fail_if: list[DetectionRule] = Field(default_factory=list)
    pass_if: list[DetectionRule] = Field(default_factory=list)
    notes: str = ""
    # Whether to include in regression suite
    regression: bool = False
    # Free-form observed_behavior — filled by runner or human reviewer
    observed_behavior: Optional[str] = None
    verdict: Optional[Verdict] = None


class CaseMeta(BaseModel):
    threat_id: str          # e.g. "T02"
    title: str
    category: str           # top-level STRIDE-like category
    subcategory: str
    severity: Severity
    exploitability: Exploitability
    threat_model_ref: str   # section reference in THREAT_MODEL.md
    residual_risk: str
    regression: bool = False


class CaseSuite(BaseModel):
    meta: CaseMeta
    cases: list[AttackCase]


class CaseResult(BaseModel):
    case_id: str
    threat_id: str
    verdict: Verdict
    observed_behavior: str
    response_status: Optional[int] = None
    response_body_excerpt: Optional[str] = None
    matched_rules: list[str] = Field(default_factory=list)
    llm_judge_reasoning: str = ""
    add_to_regression: bool = False
    executed_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow
    )
    error_detail: Optional[str] = None
