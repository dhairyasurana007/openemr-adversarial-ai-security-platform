import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { fetchAgentLog, fetchTargetEndpoint, runTargetHealthCheck } from "../api/service";
import { AttackBuilder } from "../components/AttackBuilder";
import { CampaignConfig } from "../components/CampaignConfig";
import { ChatInterface } from "../components/ChatInterface";
import { PostSession } from "../components/PostSession";
import { SessionGate } from "../components/SessionGate";
import type { TestingMode, WorkbenchMode } from "../components/SessionGate";
import { TargetInteractionPanel } from "../components/TargetInteractionPanel";
import { useApprovals } from "../hooks/useApprovals";
import { useWebSocket } from "../hooks/useWebSocket";

type SessionPhase = "pre_session" | "active" | "post_session";

const MODE_LABELS: Record<WorkbenchMode, string> = {
  manual: "Manual",
  red_team: "Red Team Agent",
  multi_sequence: "Multi-Sequence",
};

export default function Workbench() {
  const [phase, setPhase] = useState<SessionPhase>("pre_session");
  const [mode, setMode] = useState<WorkbenchMode>("manual");
  const [testingMode, setTestingMode] = useState<TestingMode>("blackbox");
  const [sessionId, setSessionId] = useState<string>(
    () => localStorage.getItem("agentforge_session_id") ?? "",
  );
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);
  const [wsEventCount, setWsEventCount] = useState(0);

  const approvals = useApprovals();
  const log = useQuery({ queryKey: ["agent-log"], queryFn: fetchAgentLog });
  const endpoint = useQuery({ queryKey: ["target-endpoint"], queryFn: fetchTargetEndpoint });

  const token = localStorage.getItem("agentforge_token") ?? "";
  const targetUrl =
    endpoint.data?.target_endpoint
    || localStorage.getItem("agentforge_target_url")
    || (__TARGET_ENDPOINT__ || "Not configured");

  useWebSocket({
    sessionId,
    token,
    enabled: Boolean(token && sessionId && (phase === "active" || phase === "post_session")),
    onEvent: () => {
      void approvals.queue.refetch();
      void log.refetch();
      setWsEventCount((n) => n + 1);
    },
  });

  const pendingApprovals = approvals.queue.data ?? [];

  useEffect(() => {
    if (phase === "active" && sessionId) {
      void runTargetHealthCheck(sessionId);
    }
  }, [sessionId, phase]);

  function startSession(selectedMode: WorkbenchMode, selectedTestingMode: TestingMode) {
    const newId = crypto.randomUUID();
    localStorage.setItem("agentforge_session_id", newId);
    setSessionId(newId);
    setMode(selectedMode);
    setTestingMode(selectedTestingMode);
    setPhase("active");
  }

  function endSession() {
    setPhase("post_session");
    setCampaignModalOpen(false);
  }

  function startNewSession() {
    setPhase("pre_session");
  }

  if (phase === "pre_session") {
    return <SessionGate onStart={startSession} />;
  }

  if (phase === "post_session") {
    return (
      <PostSession
        sessionId={sessionId}
        mode={mode}
        testingMode={testingMode}
        onNewSession={startNewSession}
        onRefetchSignal={wsEventCount}
      />
    );
  }

  const modeBadgeColor: Record<WorkbenchMode, string> = {
    manual: "var(--primary)",
    red_team: "var(--danger)",
    multi_sequence: "var(--warning)",
  };

  const sessionHeader = (
    <div
      className="page-header"
      style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 0 }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <div className="page-title">Workbench</div>
        <span
          style={{
            background: "transparent",
            border: `1px solid ${modeBadgeColor[mode]}`,
            color: modeBadgeColor[mode],
            borderRadius: "99px",
            padding: "2px 10px",
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {MODE_LABELS[mode]}
        </span>
        <span
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--text-muted)",
            borderRadius: "99px",
            padding: "2px 10px",
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {testingMode}
        </span>
        <span className="font-mono" style={{ color: "var(--text-muted)" }}>
          {sessionId.slice(0, 8)}…
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        {pendingApprovals.length > 0 && (
          <span className="badge badge-uncertain">
            {pendingApprovals.length} pending approval{pendingApprovals.length !== 1 ? "s" : ""}
          </span>
        )}
        <button type="button" className="btn btn-danger btn-sm" onClick={endSession}>
          End Session
        </button>
      </div>
    </div>
  );

  const approvalQueue = pendingApprovals.length > 0 && (
    <div className="card">
      <div className="card-title">Approval Queue</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.5rem" }}>
        {pendingApprovals.map((item) => (
          <div
            key={item.attack_id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "1rem",
              padding: "0.6rem 0.75rem",
              background: "var(--surface)",
              borderRadius: "var(--radius)",
              border: "1px solid var(--border)",
            }}
          >
            <div>
              <span className="font-mono" style={{ color: "var(--text)" }}>{item.attack_id.slice(0, 8)}…</span>
              <span className="text-muted" style={{ marginLeft: "0.75rem" }}>{item.target_category}</span>
            </div>
            <div className="flex gap-1">
              <span className={`badge badge-${item.severity_estimate.toLowerCase()}`}>{item.severity_estimate}</span>
              <button type="button" className="btn btn-success btn-xs"
                onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "approve" })}>
                Approve
              </button>
              <button type="button" className="btn btn-ghost btn-xs"
                onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "edit_approve" })}>
                Edit
              </button>
              <button type="button" className="btn btn-danger btn-xs"
                onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "reject" })}>
                Reject
              </button>
              <button type="button" className="btn btn-ghost btn-xs"
                onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "escalate_mutation" })}>
                Escalate
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // ── Manual mode ──────────────────────────────────────────────────────────
  if (mode === "manual") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {sessionHeader}
        <ChatInterface targetUrl={targetUrl} sessionId={sessionId} />
        {approvalQueue}
      </div>
    );
  }

  // ── Red Team Agent mode ──────────────────────────────────────────────────
  if (mode === "red_team") {
    return (
      <>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {sessionHeader}

          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <button
              type="button"
              className="btn btn-danger"
              onClick={() => setCampaignModalOpen(true)}
            >
              Launch Campaign
            </button>
            <span className="text-muted text-sm">Configure and dispatch a red team campaign against the target.</span>
          </div>

          <TargetInteractionPanel events={log.data ?? []} targetUrl={targetUrl} />
          {approvalQueue}
        </div>

        {/* Campaign config modal */}
        {campaignModalOpen && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1000,
              padding: "1.5rem",
            }}
            onClick={(e) => { if (e.target === e.currentTarget) setCampaignModalOpen(false); }}
          >
            <div
              style={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-lg)",
                padding: "1.5rem",
                width: "100%",
                maxWidth: 560,
                maxHeight: "85vh",
                overflow: "auto",
                position: "relative",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text)" }}>Configure Campaign</div>
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  onClick={() => setCampaignModalOpen(false)}
                >
                  ✕ Close
                </button>
              </div>
              <CampaignConfig defaultTestingMode={testingMode} onLaunched={() => setCampaignModalOpen(false)} />
            </div>
          </div>
        )}
      </>
    );
  }

  // ── Multi-Sequence mode ──────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {sessionHeader}
      <AttackBuilder />
      <ChatInterface targetUrl={targetUrl} sessionId={sessionId} />
      {approvalQueue}
    </div>
  );
}
