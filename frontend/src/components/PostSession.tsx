import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { fetchAgentLog, fetchFindings } from "../api/service";
import type { AgentEvent } from "../api/types";
import type { TestingMode, WorkbenchMode } from "./SessionGate";

interface Props {
  sessionId: string;
  mode: WorkbenchMode;
  testingMode: TestingMode;
  onNewSession: () => void;
  onRefetchSignal: number;
  interactionCount: number;
}

type StageStatus = "idle" | "running" | "complete" | "error";

interface StageCardProps {
  icon: string;
  title: string;
  status: StageStatus;
  metric?: string;
  description: string;
  isLast?: boolean;
}

const STATUS_LABEL: Record<StageStatus, string> = {
  idle: "Idle",
  running: "Processing",
  complete: "Complete",
  error: "Error",
};

const STATUS_COLOR: Record<StageStatus, string> = {
  idle: "var(--text-muted)",
  running: "var(--warning)",
  complete: "var(--success)",
  error: "var(--danger)",
};

const STATUS_BG: Record<StageStatus, string> = {
  idle: "var(--surface)",
  running: "#1c1403",
  complete: "var(--success-dim)",
  error: "var(--danger-dim)",
};

function StageCard({ icon, title, status, metric, description, isLast }: StageCardProps) {
  return (
    <div style={{ display: "flex", alignItems: "stretch", gap: 0 }}>
      <div
        className="card"
        style={{
          flex: 1,
          borderColor: status === "complete" ? "var(--success)" : status === "running" ? "var(--warning)" : "var(--border)",
          transition: "border-color 0.3s",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "0.6rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: 18 }}>{icon}</span>
            <span style={{ fontWeight: 600, fontSize: 13.5, color: "var(--text)" }}>{title}</span>
          </div>
          <span
            style={{
              background: STATUS_BG[status],
              color: STATUS_COLOR[status],
              border: `1px solid ${STATUS_COLOR[status]}`,
              borderRadius: "99px",
              padding: "1px 8px",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
            }}
          >
            {status === "running" && (
              <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--warning)", animation: "pulse 1.2s ease-in-out infinite" }} />
            )}
            {STATUS_LABEL[status]}
          </span>
        </div>
        {metric && (
          <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", lineHeight: 1, marginBottom: "0.35rem" }}>
            {metric}
          </div>
        )}
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{description}</div>
      </div>

      {!isLast && (
        <div style={{ display: "flex", alignItems: "center", padding: "0 0.5rem" }}>
          <span style={{ color: "var(--text-muted)", fontSize: 18, userSelect: "none" }}>→</span>
        </div>
      )}
    </div>
  );
}

const EVENT_LABEL: Record<string, string> = {
  "target_http.request": "Request sent",
  "target_http.response": "Response received",
  "target_http.error": "Request error",
};

function eventSummary(e: AgentEvent): string {
  const p = e.payload;
  if (e.event_type === "target_http.response") {
    return `HTTP ${String(p.status ?? "?")} · ${String(p.duration_ms ?? "?")}ms`;
  }
  if (e.event_type === "target_http.request") {
    return `POST ${String(p.url ?? "")}`;
  }
  if (e.event_type === "target_http.error") {
    return String(p.error_message ?? "Unknown error");
  }
  return e.event_type;
}

const MODE_LABELS: Record<WorkbenchMode, string> = {
  manual: "Manual",
  red_team: "Red Team Agent",
  multi_sequence: "Multi-Sequence",
};

export function PostSession({ sessionId, mode, testingMode, onNewSession, onRefetchSignal, interactionCount }: Props) {
  const navigate = useNavigate();

  const log = useQuery({
    queryKey: ["agent-log"],
    queryFn: fetchAgentLog,
    refetchInterval: 3000,
  });

  const findings = useQuery({
    queryKey: ["findings"],
    queryFn: () => fetchFindings({}),
    refetchInterval: 5000,
  });

  // Refetch whenever WebSocket fires an event
  // eslint-disable-next-line react-hooks/exhaustive-deps
  void onRefetchSignal;

  const allEvents = log.data ?? [];
  const sessionEvents = allEvents.filter((e) => e.session_id === sessionId);

  const requestCount = sessionEvents.filter((e) => e.event_type === "target_http.request").length;
  const responseCount = sessionEvents.filter((e) => e.event_type === "target_http.response").length;
  const errorCount = sessionEvents.filter((e) => e.event_type === "target_http.error").length;
  const findingCount = findings.data?.length ?? 0;

  const lastEventTime = sessionEvents.length > 0
    ? new Date(sessionEvents[0].created_at).getTime()
    : null;
  const msSinceLastEvent = lastEventTime ? Date.now() - lastEventTime : Infinity;
  const pipelineRecent = msSinceLastEvent < 5 * 60 * 1000;

  // Red Team mode: status derived from DB AgentEvent records (real data)
  const redTeamStatus: StageStatus = requestCount > 0 ? "complete" : "idle";

  // Manual / multi-sequence: manual-fire writes no DB records, so use client-side
  // interaction count as the activity signal instead
  const hasActivity = mode === "red_team" ? requestCount > 0 : interactionCount > 0;

  const judgeStatus: StageStatus =
    !hasActivity ? "idle"
    : findingCount > 0 ? "complete"
    : pipelineRecent || mode !== "red_team" ? "running"
    : "complete";

  const docStatus: StageStatus =
    !hasActivity ? "idle"
    : findingCount > 0 ? "complete"
    : judgeStatus === "running" ? "running"
    : "complete";

  const showRedTeam = mode === "red_team";

  const recentEvents = [...sessionEvents].slice(0, 20);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.3rem" }}>
            <div className="page-title">Session Ended</div>
            <span style={{ color: "var(--success)", fontSize: 18 }}>✓</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <span className="font-mono" style={{ color: "var(--text-muted)" }}>{sessionId.slice(0, 8)}…</span>
            <span className="text-muted">·</span>
            <span className="text-muted" style={{ textTransform: "capitalize" }}>{testingMode}</span>
            <span className="text-muted">·</span>
            <span className="text-muted">{MODE_LABELS[mode]}</span>
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={onNewSession}>
          Start New Session
        </button>
      </div>

      {/* Pipeline */}
      <div>
        <div className="card-title" style={{ marginBottom: "0.75rem" }}>Pipeline Status</div>
        <div style={{ display: "flex", alignItems: "stretch" }}>
          {showRedTeam && (
            <StageCard
              icon="⚔"
              title="Red Team Agent"
              status={redTeamStatus}
              metric={requestCount > 0 ? `${requestCount} attack${requestCount !== 1 ? "s" : ""}` : undefined}
              description={
                requestCount > 0
                  ? `${responseCount} response${responseCount !== 1 ? "s" : ""}${errorCount > 0 ? ` · ${errorCount} error${errorCount !== 1 ? "s" : ""}` : ""}`
                  : "No attacks fired this session."
              }
            />
          )}
          <StageCard
            icon="⚖"
            title="Judge Agent"
            status={judgeStatus}
            description={
              judgeStatus === "idle" ? "Nothing to evaluate."
              : judgeStatus === "running" ? "Evaluating session interactions against rubrics."
              : "Evaluation complete. Verdicts written."
            }
            isLast={!showRedTeam && findingCount === 0}
          />
          <StageCard
            icon="📄"
            title="Documentation Agent"
            status={docStatus}
            metric={findingCount > 0 ? `${findingCount} finding${findingCount !== 1 ? "s" : ""}` : undefined}
            description={
              docStatus === "idle" ? "Nothing to document."
              : docStatus === "running" ? "Generating vulnerability reports."
              : findingCount > 0 ? "Reports filed. Review in Findings."
              : "Processing complete."
            }
            isLast
          />
        </div>
      </div>

      {/* Live activity feed */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: "0.75rem" }}>
          Session Activity
          {log.isFetching && (
            <span style={{ marginLeft: "0.5rem", fontSize: 11, color: "var(--text-muted)", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>
              updating…
            </span>
          )}
        </div>
        {recentEvents.length === 0 ? (
          <div className="empty" style={{ padding: "1.5rem 0" }}>
            <div className="empty-text">No activity recorded for this session.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {recentEvents.map((e) => (
              <div
                key={e.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.4rem 0.6rem",
                  borderRadius: "var(--radius)",
                  background: "var(--surface)",
                  fontSize: 12.5,
                }}
              >
                <span style={{ color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace", fontSize: 11, flexShrink: 0 }}>
                  {new Date(e.created_at).toLocaleTimeString()}
                </span>
                <span
                  style={{
                    color: e.event_type === "target_http.error" ? "var(--danger)"
                      : e.event_type === "target_http.response" ? "var(--success)"
                      : "var(--primary)",
                    flexShrink: 0,
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  {EVENT_LABEL[e.event_type] ?? e.event_type}
                </span>
                <span style={{ color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {eventSummary(e)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => navigate("/findings")}
        >
          View Findings →
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => navigate("/approvals")}
        >
          View Approvals →
        </button>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
