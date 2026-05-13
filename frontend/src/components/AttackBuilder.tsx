import { useState } from "react";

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
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.75rem" }}>
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
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => move(idx, -1)} disabled={idx === 0}>↑</button>
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => move(idx, 1)} disabled={idx === turns.length - 1}>↓</button>
                <button type="button" className="btn btn-danger btn-xs" onClick={() => setTurns((prev) => prev.filter((_, i) => i !== idx))}>✕</button>
              </div>
            </div>
            <textarea
              className="form-textarea"
              value={turn.content}
              rows={3}
              placeholder={`Enter ${turn.role} message…`}
              onChange={(e) => updateTurn(idx, { content: e.target.value })}
            />
          </div>
        ))}
      </div>

      <div className="flex gap-1 mt-2">
        <button type="button" className="btn btn-secondary btn-sm"
          onClick={() => setTurns((prev) => [...prev, { role: "user", content: "" }])}>
          + Add Turn
        </button>
        <button type="button" className="btn btn-primary btn-sm"
          onClick={() => setResponse("Manual attack fired (stub response)")}>
          ⚡ Fire
        </button>
        <button type="button" className="btn btn-ghost btn-sm"
          onClick={() => setResponse("Sent to Judge (stub)")}>
          → Send to Judge
        </button>
      </div>

      {response && (
        <div className="alert alert-info mt-2">
          <span>ℹ</span> {response}
        </div>
      )}
    </div>
  );
}
