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

  return (
    <div className="card mt-2">
      <div className="card-title">Target Interaction (Live)</div>
      <div style={{ maxHeight: 320, overflow: "auto", marginTop: "0.6rem" }}>
        {targetTraffic.length === 0 ? (
          <div className="empty"><div className="empty-text">No target interaction yet</div></div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {targetTraffic.slice(0, 30).map((entry) => {
              const payload = entry.payload as Record<string, unknown>;
              const phase = entry.event_type.replace("target_http.", "");
              return (
                <div key={entry.id} style={{ border: "1px solid var(--border)", background: "var(--surface)", borderRadius: "var(--radius)", padding: "0.65rem 0.75rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                      <span className="badge badge-filed">{String(payload.method ?? "POST")}</span>
                      <span className={`badge ${phase === "error" ? "badge-critical" : phase === "response" ? "badge-patched" : "badge-uncertain"}`}>
                        {phase.toUpperCase()}
                      </span>
                      {payload.status !== undefined && (
                        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>HTTP {String(payload.status)}</span>
                      )}
                      {payload.duration_ms !== undefined && (
                        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{String(payload.duration_ms)}ms</span>
                      )}
                    </div>
                    <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                      {new Date(entry.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="font-mono text-sm" style={{ marginTop: "0.35rem", color: "var(--text)" }}>
                    {String(payload.url ?? targetUrl)}
                  </div>
                  {payload.request_body !== undefined && (
                    <pre className="font-mono text-sm" style={{ marginTop: "0.45rem", whiteSpace: "pre-wrap", wordBreak: "break-word", color: "var(--text-secondary)" }}>
                      req: {JSON.stringify(payload.request_body, null, 2)}
                    </pre>
                  )}
                  {payload.response_body !== undefined && (
                    <pre className="font-mono text-sm" style={{ marginTop: "0.35rem", whiteSpace: "pre-wrap", wordBreak: "break-word", color: "var(--text-secondary)" }}>
                      res: {JSON.stringify(payload.response_body, null, 2)}
                    </pre>
                  )}
                  {Boolean(payload.error_message) && (
                    <div className="text-sm" style={{ marginTop: "0.35rem", color: "var(--danger)" }}>
                      {String(payload.error_message)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

