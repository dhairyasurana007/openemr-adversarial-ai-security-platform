import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { fireManualAttack } from "../api/service";

type TurnRole = "user" | "system" | "assistant";

interface Turn {
  role: TurnRole;
  content: string;
}

const roleColor: Record<TurnRole, string> = {
  user: "var(--primary)",
  system: "var(--warning)",
  assistant: "var(--success)",
};

export function AttackBuilder() {
  const [turns, setTurns] = useState<Turn[]>([{ role: "user", content: "" }]);
  const [response, setResponse] = useState<string>("");
  const sessionId = localStorage.getItem("agentforge_session_id") ?? undefined;
  const hasBlankTurn = turns.some((turn) => turn.content.trim().length === 0);
  const message = turns
    .map((turn) => turn.content.trim())
    .filter((line) => line.length > 0)
    .join("\n");
  const curlPreview = `curl -X POST "$COPILOT_AGENT_BASE_URL/v1/multimodal-chat" \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json" \\
  -H "X-Clinical-Copilot-Internal-Secret: $CLINICAL_COPILOT_INTERNAL_SECRET" \\
  -d '${JSON.stringify(
    {
      message: message || "ping",
      surface: "chat",
      use_rag: true,
    },
    null,
    2,
  )}'`;

  const fireMutation = useMutation({
    mutationFn: async () => {
      return fireManualAttack({
        message: message || "ping",
        surface: "chat",
        use_rag: true,
        session_id: sessionId,
      });
    },
    onSuccess: (data) => {
      const rendered =
        typeof data.response === "string" ? data.response : JSON.stringify(data.response);
      setResponse(`HTTP ${data.status_code}: ${rendered}`);
    },
    onError: (error) => {
      setResponse(`Request failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    },
  });

  const updateTurn = (idx: number, patch: Partial<Turn>) => {
    setTurns((prev) => prev.map((turn, i) => (i === idx ? { ...turn, ...patch } : turn)));
  };

  const move = (idx: number, dir: -1 | 1) => {
    const next = idx + dir;
    if (next < 0 || next >= turns.length) return;
    setTurns((prev) => {
      const copy = [...prev];
      [copy[idx], copy[next]] = [copy[next], copy[idx]];
      return copy;
    });
  };

  return (
    <div className="card">
      <div className="card-title">Attack Sequence</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1rem", marginTop: "0.75rem" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {turns.map((turn, idx) => (
            <div key={idx} className="turn-card">
              <div className="turn-header">
                <div className="flex-center gap-1">
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: roleColor[turn.role], display: "inline-block", flexShrink: 0 }} />
                  <select className="form-select" style={{ width: "auto" }} value={turn.role}
                    onChange={(e) => updateTurn(idx, { role: e.target.value as TurnRole })}>
                    <option value="user">user</option>
                    <option value="system">system</option>
                    <option value="assistant">assistant</option>
                  </select>
                  <span className="text-muted text-sm">Turn {idx + 1}</span>
                </div>
                <div className="flex gap-1">
                  <button type="button" className="btn btn-ghost btn-xs" onClick={() => move(idx, -1)} disabled={idx === 0}>Up</button>
                  <button type="button" className="btn btn-ghost btn-xs" onClick={() => move(idx, 1)} disabled={idx === turns.length - 1}>Down</button>
                  <button type="button" className="btn btn-danger btn-xs" onClick={() => setTurns((prev) => prev.filter((_, i) => i !== idx))}>Delete</button>
                </div>
              </div>
              <textarea
                className="form-textarea"
                value={turn.content}
                rows={3}
                placeholder={`Enter ${turn.role} message...`}
                onChange={(e) => updateTurn(idx, { content: e.target.value })}
              />
            </div>
          ))}
        </div>
        <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--surface)", padding: "0.75rem" }}>
          <div className="card-title" style={{ marginBottom: "0.5rem" }}>Generated curl</div>
          <pre className="font-mono text-sm" style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", color: "var(--text-secondary)" }}>
            {curlPreview}
          </pre>
        </div>
      </div>

      <div className="flex gap-1 mt-2">
        <button type="button" className="btn btn-secondary btn-sm"
          onClick={() => setTurns((prev) => [...prev, { role: "user", content: "" }])}>
          + Add Turn
        </button>
        <button type="button" className="btn btn-primary btn-sm"
          onClick={() => fireMutation.mutate()} disabled={fireMutation.isPending || hasBlankTurn}>
          {fireMutation.isPending ? "Firing..." : "Fire"}
        </button>
        <button type="button" className="btn btn-ghost btn-sm"
          onClick={() => setResponse("Send to Judge is not wired yet.")}>
          Send to Judge
        </button>
      </div>

      {response && (
        <div className="alert alert-info mt-2">
          <span>Info</span> {response}
        </div>
      )}
    </div>
  );
}
