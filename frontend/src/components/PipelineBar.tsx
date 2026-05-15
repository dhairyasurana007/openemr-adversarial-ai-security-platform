import type { WorkbenchMode } from "./SessionGate";

export type PipelinePhase = "gate" | "active" | "post_session";

interface Props {
  mode: WorkbenchMode;
  phase: PipelinePhase;
  hasActivity: boolean;
  findingCount: number;
  judgeStarted?: boolean;
  judgeFinished?: boolean;
  docsStarted?: boolean;
  docsFinished?: boolean;
}

type StageStatus = "idle" | "active" | "complete";

const MODE_ICON: Record<WorkbenchMode, string> = {
  manual: "💬",
  red_team: "⚔",
  multi_sequence: "⚡",
};

const MODE_LABEL: Record<WorkbenchMode, string> = {
  manual: "Manual",
  red_team: "Red Team",
  multi_sequence: "Multi-Seq",
};

const STATUS_COLOR: Record<StageStatus, string> = {
  idle: "var(--text-muted)",
  active: "var(--warning)",
  complete: "var(--success)",
};

const STATUS_BORDER: Record<StageStatus, string> = {
  idle: "var(--border)",
  active: "var(--warning)",
  complete: "var(--success)",
};

const STATUS_BG: Record<StageStatus, string> = {
  idle: "var(--card)",
  active: "#1c1403",
  complete: "var(--success-dim)",
};

interface StageProps {
  icon: string;
  label: string;
  sublabel?: string;
  status: StageStatus;
  metric?: string;
}

function Stage({ icon, label, sublabel, status, metric }: StageProps) {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.5rem 0.75rem",
        borderRadius: "var(--radius)",
        border: `1px solid ${STATUS_BORDER[status]}`,
        background: STATUS_BG[status],
        transition: "border-color 0.3s, background 0.3s",
        minWidth: 0,
      }}
    >
      <span style={{ fontSize: 14, flexShrink: 0 }}>{icon}</span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: STATUS_COLOR[status],
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
          }}
        >
          {status === "active" && (
            <span
              style={{
                display: "inline-block",
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: "var(--warning)",
                animation: "pipeline-pulse 1.2s ease-in-out infinite",
                flexShrink: 0,
              }}
            />
          )}
          {label}
        </div>
        {sublabel && (
          <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {sublabel}
          </div>
        )}
        {metric && (
          <div style={{ fontSize: 10, color: STATUS_COLOR[status], marginTop: 1, fontWeight: 600 }}>
            {metric}
          </div>
        )}
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div style={{ display: "flex", alignItems: "center", padding: "0 0.25rem", flexShrink: 0 }}>
      <span style={{ color: "var(--text-muted)", fontSize: 12, userSelect: "none" }}>→</span>
    </div>
  );
}

export function PipelineBar({ mode, phase, hasActivity, findingCount, judgeStarted, judgeFinished, docsStarted, docsFinished }: Props) {
  const isPost = phase === "post_session";
  const isActive = phase === "active";

  const modeStatus: StageStatus =
    phase === "gate" ? "idle"
    : isActive ? "active"
    : hasActivity ? "complete"
    : "idle";

  const judgeStatus: StageStatus =
    !hasActivity ? "idle"
    : findingCount > 0 || judgeFinished ? "complete"
    : judgeStarted ? "active"
    : isPost ? "active"
    : "idle";

  const docStatus: StageStatus =
    !hasActivity ? "idle"
    : findingCount > 0 || docsFinished ? "complete"
    : docsStarted ? "active"
    : judgeStatus === "complete" ? "active"
    : "idle";

  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "stretch",
          gap: 0,
          background: "var(--bg)",
          borderBottom: "1px solid var(--border)",
          padding: "0.5rem 0",
        }}
      >
        <Stage
          icon={MODE_ICON[mode]}
          label={MODE_LABEL[mode]}
          sublabel={modeStatus === "active" ? "In progress" : modeStatus === "complete" ? "Done" : "Waiting"}
          status={modeStatus}
        />
        <Arrow />
        <Stage
          icon="⚖"
          label="Judge"
          sublabel={
            judgeStatus === "active" ? "Evaluating…"
            : judgeStatus === "complete" ? "Verdicts written"
            : "Waiting"
          }
          status={judgeStatus}
        />
        <Arrow />
        <Stage
          icon="📄"
          label="Docs"
          sublabel={
            docStatus === "active" ? "Generating reports…"
            : docStatus === "complete" ? "Reports filed"
            : "Waiting"
          }
          metric={findingCount > 0 ? `${findingCount} finding${findingCount !== 1 ? "s" : ""}` : undefined}
          status={docStatus}
        />
      </div>
      <style>{`
        @keyframes pipeline-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </>
  );
}
