import { useMemo, useState } from "react";

import { useApprovals } from "../hooks/useApprovals";
import { useFindings } from "../hooks/useFindings";

export default function Findings() {
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const findings = useFindings({ severity: severity || undefined, status: status || undefined });
  const approvals = useApprovals();

  const selected = useMemo(
    () => (findings.data ?? []).find((item) => item.id === selectedId) ?? null,
    [findings.data, selectedId],
  );

  return (
    <section>
      <h2>Findings</h2>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="DRAFT">DRAFT</option>
          <option value="FILED">FILED</option>
          <option value="PATCHED">PATCHED</option>
          <option value="VALIDATED">VALIDATED</option>
        </select>
      </div>

      {findings.data?.length ? (
        <table style={{ width: "100%" }}>
          <thead>
            <tr>
              <th align="left">Severity</th>
              <th align="left">Status</th>
              <th align="left">Category</th>
            </tr>
          </thead>
          <tbody>
            {findings.data.map((item) => (
              <tr key={item.id} onClick={() => setSelectedId(item.id)} style={{ cursor: "pointer" }}>
                <td>{item.severity}</td>
                <td>{item.status}</td>
                <td>{item.attack_category}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No findings yet</p>
      )}

      {selected ? (
        <aside style={{ marginTop: "1rem", borderTop: "1px solid #ddd", paddingTop: "1rem" }}>
          <h3>Details: {selected.id}</h3>
          <pre>{JSON.stringify(selected, null, 2)}</pre>
          {selected.severity === "CRITICAL" && selected.status === "DRAFT" ? (
            <button
              type="button"
              onClick={() => approvals.reportDecision.mutate({ reportId: selected.id, decision: "approve" })}
            >
              Approve
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              const blob = new Blob([JSON.stringify(selected, null, 2)], { type: "application/json" });
              const link = document.createElement("a");
              link.href = URL.createObjectURL(blob);
              link.download = `finding-${selected.id}.json`;
              link.click();
              URL.revokeObjectURL(link.href);
            }}
          >
            Download JSON
          </button>
        </aside>
      ) : null}
    </section>
  );
}
