import type { AgentEvent } from "../api/types";

interface TargetInteractionPanelProps {
  events: AgentEvent[];
  targetUrl: string;
}

export function TargetInteractionPanel({ events, targetUrl }: TargetInteractionPanelProps) {
  const targetTraffic = events.filter((e) =>
    e.event_type === "target_http.request"
    || e.event_type === "target_http.response"
    || e.event_type === "target_http.error",
  );
  const latest = targetTraffic.slice(0, 40).reverse();

  return (
    <div className="card mt-2">
      <div className="card-title">Target Interaction (Live)</div>
      <div className="card-meta" style={{ marginTop: "0.35rem" }}>
        Endpoint: <span className="font-mono">{targetUrl}</span>
      </div>
      <div style={{ maxHeight: 360, overflow: "auto", marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.7rem" }}>
        <div style={{ alignSelf: "flex-start", maxWidth: "85%", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "14px", padding: "0.6rem 0.75rem" }}>
          <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Connected to target. Workbench auto-sends a health check when opened.
          </div>
        </div>
        {latest.map((entry) => {
          const payload = entry.payload as Record<string, unknown>;
          const phase = entry.event_type.replace("target_http.", "");
          const isRequest = phase === "request";
          const bubbleBg = isRequest ? "var(--primary)" : "var(--surface)";
          const bubbleColor = isRequest ? "#ffffff" : "var(--text)";
          const align = isRequest ? "flex-end" : "flex-start";
          const text =
            phase === "request"
              ? JSON.stringify(payload.request_body ?? {}, null, 2)
              : phase === "response"
                ? JSON.stringify(payload.response_body ?? {}, null, 2)
                : String(payload.error_message ?? "Unknown target error");
          return (
            <div key={entry.id} style={{ alignSelf: align, maxWidth: "90%" }}>
              <div style={{ borderRadius: "14px", padding: "0.65rem 0.8rem", background: bubbleBg, color: bubbleColor, border: isRequest ? "none" : "1px solid var(--border)" }}>
                <div className="text-sm" style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                  {isRequest ? "You -> Target" : phase === "response" ? "Target -> You" : "Target Error"}
                </div>
                <pre className="font-mono text-sm" style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", color: bubbleColor }}>
                  {text}
                </pre>
              </div>
              <div className="text-sm" style={{ marginTop: "0.2rem", color: "var(--text-muted)", textAlign: isRequest ? "right" : "left" }}>
                {new Date(entry.created_at).toLocaleTimeString()}
                {payload.status !== undefined ? ` • HTTP ${String(payload.status)}` : ""}
                {payload.duration_ms !== undefined ? ` • ${String(payload.duration_ms)}ms` : ""}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
