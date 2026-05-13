from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import UUID4, BaseModel, Field


class BaseMessage(BaseModel):
    source_agent: Literal["orchestrator", "red_team", "judge", "documentation", "human"]
    target_agent: Literal["red_team", "judge", "documentation", "human", "broadcast"]
    message_type: str
    session_id: UUID4
    cost_so_far: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CampaignDirective(BaseMessage):
    message_type: Literal["CAMPAIGN_DIRECTIVE"] = "CAMPAIGN_DIRECTIVE"
    campaign_id: UUID4
    target_category: str
    technique_ids: list[str]
    seed_case_ids: list[str]
    mutation_depth: int
    cost_cap_usd: float
    testing_mode: Literal["whitebox", "blackbox"]
    execution_mode: Literal["auto", "permissions"]
    connection_path: Literal["copilot_endpoint", "fastapi_direct"]


class AttackResult(BaseMessage):
    message_type: Literal["ATTACK_RESULT"] = "ATTACK_RESULT"
    attack_id: UUID4
    campaign_id: UUID4
    threat_id: str
    prompt_sequence: list[dict]
    target_response: str
    response_status_code: int
    token_cost_usd: float


class JudgeVerdict(BaseMessage):
    message_type: Literal["JUDGE_VERDICT"] = "JUDGE_VERDICT"
    attack_id: UUID4
    verdict: Literal["SUCCESS", "PARTIAL", "FAILURE", "UNCERTAIN"]
    confidence: float
    evidence_excerpt: str
    layer_triggered: Literal["rule_engine", "llm_consensus", "human"]
    regression_flag: bool = False


class Escalation(BaseMessage):
    message_type: Literal["ESCALATION"] = "ESCALATION"
    attack_id: UUID4
    reason: str


class RegressionFlag(BaseMessage):
    message_type: Literal["REGRESSION_FLAG"] = "REGRESSION_FLAG"
    attack_id: UUID4
    previous_verdict: str
    current_verdict: str


class HumanApprovalRequest(BaseMessage):
    """Permissions mode: agent requests operator approval before firing attack."""

    message_type: Literal["HUMAN_APPROVAL_REQUEST"] = "HUMAN_APPROVAL_REQUEST"
    attack_id: UUID4
    campaign_id: UUID4
    proposed_sequence: list[dict]
    technique_id: str
    target_category: str
    severity_estimate: str


class HumanApprovalResponse(BaseMessage):
    message_type: Literal["HUMAN_APPROVAL_RESPONSE"] = "HUMAN_APPROVAL_RESPONSE"
    attack_id: UUID4
    decision: Literal["approve", "reject", "edit_approve", "escalate_mutation"]
    edited_sequence: list[dict] | None = None
    operator_user_id: UUID4


class AttackApprovalRequest(BaseMessage):
    """CRITICAL report: CISO/Security Lead approval before filing."""

    message_type: Literal["ATTACK_APPROVAL_REQUEST"] = "ATTACK_APPROVAL_REQUEST"
    vulnerability_id: UUID4


class AttackApprovalResponse(BaseMessage):
    message_type: Literal["ATTACK_APPROVAL_RESPONSE"] = "ATTACK_APPROVAL_RESPONSE"
    vulnerability_id: UUID4
    decision: Literal["approve", "reject"]
    approver_user_id: UUID4


STREAM_MAP: dict[str, list[str]] = {
    "orchestrator": ["CAMPAIGN_DIRECTIVE", "REGRESSION_FLAG"],
    "red_team": ["CAMPAIGN_DIRECTIVE", "HUMAN_APPROVAL_RESPONSE"],
    "judge": ["ATTACK_RESULT"],
    "documentation": ["JUDGE_VERDICT"],
    "human": ["HUMAN_APPROVAL_REQUEST", "ATTACK_APPROVAL_REQUEST", "ESCALATION"],
}
