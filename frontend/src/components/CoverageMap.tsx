import type { CoverageMap as CoverageMapRow } from "../api/types";

function riskClass(risk: string) {
  return { CRITICAL: "danger", HIGH: "warning", MEDIUM: "warning", LOW: "success" }[risk] ?? "success";
}

export function CoverageMap({ rows }: { rows: CoverageMapRow[] }) {
  if (rows.length === 0) {
    return <div className="empty"><div className="empty-text">No coverage data yet</div></div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {rows.map((row) => {
        const ratio = row.total_attacks > 0 ? row.success_count / row.total_attacks : 0;
        return (
          <div key={row.attack_category}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ color: "var(--text)", fontSize: 13, fontWeight: 500 }}>{row.attack_category}</span>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="text-muted text-sm">{row.total_attacks} attacks</span>
                <span className={`badge badge-${row.residual_risk.toLowerCase()}`}>{row.residual_risk}</span>
              </div>
            </div>
            <div className="progress-bar">
              <div
                className={`progress-fill ${riskClass(row.residual_risk)}`}
                style={{ width: `${Math.round(ratio * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
