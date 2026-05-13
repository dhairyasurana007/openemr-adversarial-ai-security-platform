import { useState } from "react";

type TurnRole = "user" | "system" | "assistant";

interface Turn {
  role: TurnRole;
  content: string;
}

export function AttackBuilder() {
  const [turns, setTurns] = useState<Turn[]>([{ role: "user", content: "" }]);
  const [response, setResponse] = useState<string>("");

  const updateTurn = (idx: number, patch: Partial<Turn>) => {
    setTurns((prev) => prev.map((turn, i) => (i === idx ? { ...turn, ...patch } : turn)));
  };

  const move = (idx: number, dir: -1 | 1) => {
    const next = idx + dir;
    if (next < 0 || next >= turns.length) {
      return;
    }
    setTurns((prev) => {
      const copy = [...prev];
      [copy[idx], copy[next]] = [copy[next], copy[idx]];
      return copy;
    });
  };

  return (
    <section>
      <h3>Attack Builder</h3>
      {turns.map((turn, idx) => (
        <div key={idx} style={{ border: "1px solid #ddd", marginBottom: "0.5rem", padding: "0.5rem" }}>
          <select
            value={turn.role}
            onChange={(e) => updateTurn(idx, { role: e.target.value as TurnRole })}
          >
            <option value="user">user</option>
            <option value="system">system</option>
            <option value="assistant">assistant</option>
          </select>
          <textarea
            value={turn.content}
            onChange={(e) => updateTurn(idx, { content: e.target.value })}
            rows={3}
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="button" onClick={() => move(idx, -1)}>
              Up
            </button>
            <button type="button" onClick={() => move(idx, 1)}>
              Down
            </button>
            <button type="button" onClick={() => setTurns((prev) => prev.filter((_, i) => i !== idx))}>
              Remove
            </button>
          </div>
        </div>
      ))}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" onClick={() => setTurns((prev) => [...prev, { role: "user", content: "" }])}>
          Add Turn
        </button>
        <button type="button" onClick={() => setResponse("Manual attack fired (stub response)")}>Fire</button>
        <button type="button" onClick={() => setResponse("Sent to Judge (stub)")}>Send to Judge</button>
      </div>
      {response ? <pre>{response}</pre> : null}
    </section>
  );
}
