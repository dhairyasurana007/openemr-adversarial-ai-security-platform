import type { CoverageMap as CoverageMapRow } from "../api/types";

const riskColor: Record<string, string> = {
  CRITICAL: "#b91c1c",
  HIGH: "#ea580c",
  MEDIUM: "#ca8a04",
  LOW: "#16a34a",
};

export function CoverageMap({ rows }: { rows: CoverageMapRow[] }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th align="left">Category</th>
          <th align="left">Coverage</th>
          <th align="left">Residual Risk</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const ratio = row.total_attacks > 0 ? row.success_count / row.total_attacks : 0;
          return (
            <tr key={row.attack_category}>
              <td>{row.attack_category}</td>
              <td>
                <progress max={1} value={ratio} style={{ width: "100%" }} />
              </td>
              <td style={{ color: riskColor[row.residual_risk] ?? "#000" }}>{row.residual_risk}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
