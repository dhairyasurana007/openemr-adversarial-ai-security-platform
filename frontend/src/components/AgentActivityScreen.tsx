import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { finalizeSession } from "../api/service";
import type { AgentEvent } from "../api/types";
import { PipelineBar } from "./PipelineBar";
import type { PipelinePhase } from "./PipelineBar";
import type { TestingMode, WorkbenchMode } from "./SessionGate";

interface Props {
  sessionId: string;
  mode: WorkbenchMode;
  testingMode: TestingMode;
  sessionEvents: AgentEvent[];
  findingCount: number;
  onNewSession: () => void;
}

const MODE_LABELS: Record<WorkbenchMode, string> = {
  manual: "Manual",
  red_team: "Red Team Agent",
  multi_sequence: "Multi-Sequence",
};

const VERDICT_COLOR: Record<string, string> = {
  SUCCESS: "var(--danger)",
  PARTIAL: "var(--warning)",
  FAILURE: "var(--success)",
  UNCERTAIN: "var(--text-muted)",
};

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "var(--danger)",
  HIGH: "var(--danger)",
  MEDIUM: "var(--warning)",
  LOW: "var(--success)",
};

function EventRow({ time, label, detail, color }: { time: string; label: string; detail?: string; color?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", padding: "0.3rem 0", borderBottom: "1px solid var(--border)", fontSize: 12.5 }}>
      <span style={{ color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace", fontSize: 11, flexShrink: 0 }}>
        {time}
      </span>
      <span style={{ color: color ?? "var(--text)", fontWeight: 600, flexShrink: 0, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </span>
      {detail && (
        <span style={{ color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {detail}
        </span>
      )}
    </div>
  );
}

function AgentCard({
  icon, title, status, events,
}: {
  icon: string;
  title: string;
  status: "idle" | "running" | "complete";
  events: AgentEvent[];
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const borderColor =
    status === "complete" ? "var(--success)"
    : status === "running" ? "var(--warning)"
    : "var(--border)";

  const statusLabel =
    status === "running" ? "Processing"
    : status === "complete" ? "Complete"
    : "Waiting";

  const statusColor =
    status === "running" ? "var(--warning)"
    : status === "complete" ? "var(--success)"
    : "var(--text-muted)";

  return (
    <div className="card" style={{ flex: 1, borderColor, transition: "border-color 0.3s" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: 16 }}>{icon}</span>
          <span style={{ fontWeight: 600, fontSize: 13.5, color: "var(--text)" }}>{title}</span>
        </div>
        <span style={{
          display: "flex", alignItems: "center", gap: "0.35rem",
          background: status === "running" ? "#1c1403" : status === "complete" ? "var(--success-dim)" : "var(--surface)",
          color: statusColor,
          border: `1px solid ${statusColor}`,
          borderRadius: "99px", padding: "1px 8px",
          fontSize: 10, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase",
        }}>
          {status === "running" && (
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--warning)", animation: "activity-pulse 1.2s ease-in-out infinite", display: "inline-block", flexShrink: 0 }} />
          )}
          {statusLabel}
        </span>
      </div>

      <div
        ref={scrollRef}
        style={{ height: 180, overflowY: "auto", display: "flex", flexDirection: "column", paddingRight: "0.25rem" }}
      >
        {events.length === 0 ? (
          <div style={{ margin: "auto", color: "var(--text-muted)", fontSize: 12, textAlign: "center" }}>
            {status === "idle" ? "Waiting for session to finalize…" : "No events yet"}
          </div>
        ) : (
          events.map((e) => {
            const ts = new Date(e.created_at).toLocaleTimeString();
            const p = e.payload as Record<string, unknown>;

            if (e.event_type === "judge.evaluation_started") {
              return <EventRow key={e.id} time={ts} label="started" detail={`Evaluating interaction · category: ${String(p.category ?? "")}`} color="var(--primary)" />;
            }
            if (e.event_type === "judge.verdict_saved") {
              const verdict = String(p.verdict ?? "");
              const conf = typeof p.confidence === "number" ? `${Math.round(p.confidence * 100)}%` : "";
              return <EventRow key={e.id} time={ts} label={verdict} detail={conf ? `confidence ${conf}` : undefined} color={VERDICT_COLOR[verdict] ?? "var(--text)"} />;
            }
            if (e.event_type === "documentation.report_started") {
              return <EventRow key={e.id} time={ts} label="started" detail="Generating vulnerability report…" color="var(--primary)" />;
            }
            if (e.event_type === "documentation.report_saved") {
              const severity = String(p.severity ?? "");
              const status = String(p.status ?? "");
              return <EventRow key={e.id} time={ts} label="filed" detail={`${severity} · ${status}`} color={SEVERITY_COLOR[severity] ?? "var(--text)"} />;
            }
            return null;
          })
        )}
      </div>
    </div>
  );
}

export function AgentActivityScreen({ sessionId, mode, testingMode, sessionEvents, findingCount, onNewSession }: Props) {
  const navigate = useNavigate();
  const [docsReady, setDocsReady] = useState(false);
  const graceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalizedRef = useRef(false);

  // Call finalize-session exactly once per session
  useEffect(() => {
    if (!sessionId || finalizedRef.current) return;
    const key = "agentforge_finalized_session";
    if (localStorage.getItem(key) === sessionId) {
      finalizedRef.current = true;
      return;
    }
    finalizedRef.current = true;
    void finalizeSession(sessionId)
      .then(() => {
        localStorage.setItem(key, sessionId);
      })
      .catch((err) => {
        console.error("[AgentActivityScreen] finalize-session failed:", err);
        finalizedRef.current = false; // allow retry on next render
      });
  }, [sessionId]);

  const finalizedEvent = sessionEvents.find((e) => e.event_type === "session.finalized");
  const totalAttacks: number = typeof (finalizedEvent?.payload as Record<string, unknown>)?.total_attacks === "number"
    ? (finalizedEvent!.payload as Record<string, unknown>).total_attacks as number
    : -1; // -1 = unknown (event not yet received)

  const judgeStarted = sessionEvents.some((e) => e.event_type === "judge.evaluation_started");
  const judgeVerdictCount = sessionEvents.filter((e) => e.event_type === "judge.verdict_saved").length;
  const judgeComplete =
    (totalAttacks === 0) ||
    (totalAttacks > 0 && judgeVerdictCount >= totalAttacks);

  const docsStarted = sessionEvents.some((e) => e.event_type === "documentation.report_started");
  const docsFinished = sessionEvents.some((e) => e.event_type === "documentation.report_saved");

  const judgeStatus: "idle" | "running" | "complete" =
    !judgeStarted && !judgeComplete ? "idle"
    : judgeComplete ? "complete"
    : "running";

  const docsStatus: "idle" | "running" | "complete" =
    docsFinished ? "complete"
    : docsStarted ? "running"
    : "idle";

  // After judge finishes, give docs a 6-second grace window to start.
  // If it doesn't start, there's nothing to document → show buttons.
  useEffect(() => {
    if (docsReady) return;
    if (docsFinished) { setDocsReady(true); return; }
    if (judgeComplete && !docsStarted) {
      graceTimerRef.current = setTimeout(() => setDocsReady(true), 6000);
    }
    return () => {
      if (graceTimerRef.current) clearTimeout(graceTimerRef.current);
    };
  }, [judgeComplete, docsStarted, docsFinished, docsReady]);

  const pipelinePhase: PipelinePhase = "post_session";
  const hasActivity = judgeStarted || totalAttacks > 0;

  const judgeFilteredEvents = sessionEvents.filter((e) => ["judge.evaluation_started", "judge.verdict_saved"].includes(e.event_type));
  const docsFilteredEvents = sessionEvents.filter((e) => ["documentation.report_started", "documentation.report_saved"].includes(e.event_type));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <PipelineBar
        mode={mode}
        phase={pipelinePhase}
        hasActivity={hasActivity}
        findingCount={findingCount}
        judgeStarted={judgeStarted}
        judgeFinished={judgeComplete}
        docsStarted={docsStarted}
        docsFinished={docsFinished}
      />

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
            {totalAttacks >= 0 && (
              <>
                <span className="text-muted">·</span>
                <span className="text-muted">{judgeVerdictCount}/{totalAttacks} evaluated</span>
              </>
            )}
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={onNewSession}>
          Start New Session
        </button>
      </div>

      {/* Agent cards */}
      <div style={{ display: "flex", gap: "1rem" }}>
        <AgentCard icon="⚖" title="Judge Agent" status={judgeStatus} events={judgeFilteredEvents} />
        <AgentCard icon="📄" title="Documentation Agent" status={docsStatus} events={docsFilteredEvents} />
      </div>

      {/* Action buttons — only after docs pipeline is done */}
      {docsReady && (
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="button" className="btn btn-secondary" onClick={() => navigate("/findings")}>
            View Findings →
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate("/approvals")}>
            View Approvals →
          </button>
        </div>
      )}

      <style>{`
        @keyframes activity-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
