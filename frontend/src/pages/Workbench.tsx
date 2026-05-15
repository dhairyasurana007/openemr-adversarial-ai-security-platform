import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { fetchAgentLog, fetchTargetEndpoint, runTargetHealthCheck } from "../api/service";
import { AttackBuilder } from "../components/AttackBuilder";
import { CampaignConfig } from "../components/CampaignConfig";
import { ChatInterface } from "../components/ChatInterface";
import { SeedManager } from "../components/SeedManager";
import { SessionGate } from "../components/SessionGate";
import type { TestingMode, WorkbenchMode } from "../components/SessionGate";
import { TargetInteractionPanel } from "../components/TargetInteractionPanel";
import { useApprovals } from "../hooks/useApprovals";
import { useWebSocket } from "../hooks/useWebSocket";

type SessionPhase = "pre_session" | "active";

const sidebarTabs = ["Campaign Config", "Seed Manager", "Replay"] as const;
type SidebarTab = (typeof sidebarTabs)[number];

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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("Campaign Config");
  const [replayQuery, setReplayQuery] = useState("");

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
    enabled: Boolean(token && sessionId && phase === "active"),
    onEvent: () => {
      void approvals.queue.refetch();
      void log.refetch();
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
    setPhase("pre_session");
    setCampaignModalOpen(false);
    setSidebarOpen(false);
  }

  if (phase === "pre_session") {
    return <SessionGate onStart={startSession} />;
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
        {mode !== "multi_sequence" && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setSidebarOpen((v) => !v)}
          >
            {sidebarOpen ? "Hide Tools" : "Advanced Tools"}
          </button>
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

  const advancedSidebar = sidebarOpen && (
    <div style={{ width: 400, flexShrink: 0, display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <div className="tabs" style={{ width: "100%", flexWrap: "wrap" }}>
        {sidebarTabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={`tab${activeTab === tab ? " active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      {activeTab === "Campaign Config" && <CampaignConfig defaultTestingMode={testingMode} />}
      {activeTab === "Seed Manager" && <SeedManager />}
      {activeTab === "Replay" && (
        <div className="card">
          <div className="card-title">Replay Attack</div>
          <div className="form-group mt-1">
            <label className="form-label">Attack ID or Category</label>
            <input
              className="form-input"
              value={replayQuery}
              onChange={(e) => setReplayQuery(e.target.value)}
              placeholder="e.g. T01-001 or prompt_injection"
            />
          </div>
          <button type="button" className="btn btn-primary mt-2">Replay</button>
          {replayQuery && (
            <p className="text-muted mt-1">Query: <span className="font-mono">{replayQuery}</span></p>
          )}
        </div>
      )}
    </div>
  );

  // ── Manual mode ──────────────────────────────────────────────────────────
  if (mode === "manual") {
    return (
      <div style={{ display: "flex", gap: "1.25rem", alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "1rem" }}>
          {sessionHeader}
          <ChatInterface targetUrl={targetUrl} sessionId={sessionId} />
          {approvalQueue}
        </div>
        {advancedSidebar}
      </div>
    );
  }

  // ── Red Team Agent mode ──────────────────────────────────────────────────
  if (mode === "red_team") {
    return (
      <>
        <div style={{ display: "flex", gap: "1.25rem", alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "1rem" }}>
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
          {advancedSidebar}
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
