from __future__ import annotations

import asyncio
from typing import Annotated, Any, TypedDict
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from agents.documentation.agent import DocumentationAgent
from agents.judge.agent import JudgeAgent
from agents.orchestrator.agent import OrchestratorAgent
from agents.red_team.agent import RedTeamAgent
from orchestration.messages import AttackApprovalResponse, HumanApprovalResponse, JudgeVerdict
from state.models.vulnerability import VulnerabilityReport


class PlatformState(TypedDict, total=False):
    session_id: UUID
    campaign_id: UUID | None
    execution_mode: str
    pending_attacks: list[UUID]
    pending_approvals: list[UUID]
    current_attack_id: UUID | None
    last_verdict: str | None
    messages: Annotated[list, add_messages]
    done: bool
    directive: Any | None
    attack_record: Any | None
    verdict_row: Any | None
    report: VulnerabilityReport | None
    approval_response: HumanApprovalResponse | None
    critical_approval_response: AttackApprovalResponse | None
    run_regression: bool


class AgentGraph:
    def __init__(
        self,
        orchestrator: OrchestratorAgent | None = None,
        red_team: RedTeamAgent | None = None,
        judge: JudgeAgent | None = None,
        documentation: DocumentationAgent | None = None,
    ) -> None:
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.red_team = red_team or RedTeamAgent()
        self.judge = judge or JudgeAgent()
        self.documentation = documentation or DocumentationAgent()
        self.app = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(PlatformState)
        graph.add_node("orchestrate", self.orchestrate)
        graph.add_node("generate_attack", self.generate_attack)
        graph.add_node("await_approval", self.await_approval)
        graph.add_node("execute_attack", self.execute_attack)
        graph.add_node("evaluate", self.evaluate)
        graph.add_node("mutate", self.mutate)
        graph.add_node("document", self.document)
        graph.add_node("await_critical_approval", self.await_critical_approval)
        graph.add_node("run_regression", self.run_regression)

        graph.add_edge(START, "orchestrate")
        graph.add_conditional_edges("orchestrate", self._route_after_orchestrate)
        graph.add_conditional_edges("generate_attack", self._route_after_generate_attack)
        graph.add_conditional_edges("await_approval", self._route_after_await_approval)
        graph.add_edge("execute_attack", "evaluate")
        graph.add_conditional_edges("evaluate", self._route_after_evaluate)
        graph.add_conditional_edges("mutate", self._route_after_mutate)
        graph.add_conditional_edges("document", self._route_after_document)
        graph.add_edge("await_critical_approval", "orchestrate")
        graph.add_edge("run_regression", "orchestrate")

        return graph.compile(checkpointer=InMemorySaver())

    async def _next_directive(self, session_id: UUID):
        async with self.orchestrator.session_maker() as db:
            return await self.orchestrator.prioritizer.next_directive(db, session_id=session_id)

    async def orchestrate(self, state: PlatformState) -> dict[str, Any]:
        if state.get("run_regression"):
            return {"done": False}

        session_id = state.get("session_id") or uuid4()
        directive = await self._next_directive(session_id)
        if directive is None:
            return {"done": True, "session_id": session_id, "directive": None}

        return {
            "done": False,
            "session_id": session_id,
            "campaign_id": directive.campaign_id,
            "execution_mode": directive.execution_mode,
            "directive": directive,
        }

    async def generate_attack(self, state: PlatformState) -> dict[str, Any]:
        directive = state["directive"]
        sequence, token_cost = self.red_team.generate_sequence(directive)
        return {
            "attack_sequence": sequence,
            "token_cost_usd": token_cost,
        }

    async def await_approval(self, state: PlatformState) -> dict[str, Any]:
        approval_raw = interrupt("awaiting_operator_approval")
        approval = HumanApprovalResponse.model_validate(approval_raw)
        return {"approval_response": approval}

    async def execute_attack(self, state: PlatformState) -> dict[str, Any]:
        directive = state["directive"]
        sequence = state["attack_sequence"]
        if directive.execution_mode == "permissions":
            approval = state.get("approval_response")
            if approval is None:
                return {"done": True}
            if approval.decision == "reject":
                return {"done": True}
            if approval.decision == "edit_approve" and approval.edited_sequence:
                sequence = approval.edited_sequence
            if approval.decision == "escalate_mutation":
                directive = directive.model_copy(
                    update={"mutation_depth": directive.mutation_depth + 1}
                )
                sequence, _ = self.red_team.generate_sequence(directive)

        status_code, target_response = await self.red_team.execute_attack(
            sequence, directive.connection_path
        )
        attack_record = {
            "id": uuid4(),
            "campaign_id": directive.campaign_id,
            "session_id": directive.session_id,
            "threat_id": (
                directive.seed_case_ids[0].split("-")[0] if directive.seed_case_ids else "UNKNOWN"
            ),
            "attack_category": directive.target_category,
            "technique_id": directive.technique_ids[0] if directive.technique_ids else None,
            "prompt_sequence": sequence,
            "target_response": target_response,
            "response_status_code": status_code,
            "connection_path": directive.connection_path,
            "testing_mode": directive.testing_mode,
            "token_cost_usd": state.get("token_cost_usd", 0.0),
            "is_variant": False,
            "parent_attack_id": None,
        }
        return {"attack_record": attack_record, "current_attack_id": attack_record["id"]}

    async def evaluate(self, state: PlatformState) -> dict[str, Any]:
        attack = state["attack_record"]
        verdict = await self.judge.evaluate(attack)
        return {"verdict_row": verdict, "last_verdict": str(verdict.verdict)}

    async def mutate(self, state: PlatformState) -> dict[str, Any]:
        pending = list(state.get("pending_attacks", []))
        pending.append(uuid4())
        return {"pending_attacks": pending}

    async def document(self, state: PlatformState) -> dict[str, Any]:
        verdict = state["verdict_row"]
        verdict_msg = JudgeVerdict(
            source_agent="judge",
            target_agent="documentation",
            session_id=state["session_id"],
            attack_id=state["current_attack_id"],
            verdict=verdict.verdict,
            confidence=float(verdict.confidence),
            evidence_excerpt=verdict.evidence_excerpt,
            layer_triggered=verdict.layer_triggered,
            regression_flag=bool(verdict.regression_flag),
        )
        report = await self.documentation.generate_report(verdict_msg)
        return {"report": report}

    async def await_critical_approval(self, state: PlatformState) -> dict[str, Any]:
        approval_raw = interrupt("awaiting_critical_report_approval")
        approval = AttackApprovalResponse.model_validate(approval_raw)
        return {"critical_approval_response": approval}

    async def run_regression(self, _state: PlatformState) -> dict[str, Any]:
        return {"run_regression": False}

    def _route_after_orchestrate(self, state: PlatformState) -> str:
        if state.get("done"):
            return END
        if state.get("run_regression"):
            return "run_regression"
        return "generate_attack"

    def _route_after_generate_attack(self, state: PlatformState) -> str:
        if state.get("execution_mode") == "permissions":
            return "await_approval"
        return "execute_attack"

    def _route_after_await_approval(self, state: PlatformState) -> str:
        approval = state.get("approval_response")
        if approval is None or approval.decision == "reject":
            return END
        return "execute_attack"

    def _route_after_evaluate(self, state: PlatformState) -> str:
        verdict = str(state.get("last_verdict") or "").upper()
        if verdict == "PARTIAL":
            return "mutate"

        if verdict == "SUCCESS":
            confidence = float(getattr(state.get("verdict_row"), "confidence", 0.0))
            if confidence >= 0.85:
                return "document"
        return "orchestrate"

    def _route_after_mutate(self, state: PlatformState) -> str:
        return "execute_attack" if state.get("pending_attacks") else "orchestrate"

    def _route_after_document(self, state: PlatformState) -> str:
        report = state.get("report")
        if report is not None and str(report.severity).upper() == "CRITICAL":
            return "await_critical_approval"
        return "orchestrate"

    async def run(self) -> None:
        print("AgentGraph started")
        print("Waiting for campaign directive...")
        while True:
            initial_state: PlatformState = {
                "session_id": uuid4(),
                "campaign_id": None,
                "execution_mode": "auto",
                "pending_attacks": [],
                "pending_approvals": [],
                "current_attack_id": None,
                "last_verdict": None,
                "messages": [],
                "done": False,
                "run_regression": False,
            }
            await self.app.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": str(uuid4())}},
            )
            await asyncio.sleep(1)
