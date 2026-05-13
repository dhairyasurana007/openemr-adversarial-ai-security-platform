const verdictClass: Record<string, string> = {
  SUCCESS: "badge-success",
  FAILURE: "badge-failure",
  PARTIAL: "badge-partial",
  UNCERTAIN: "badge-uncertain",
};

export function VerdictTrend({
  points,
}: {
  points: Array<{ day: string; verdict: string; count: number }>;
}) {
  if (points.length === 0) {
    return <div className="empty"><div className="empty-text">No verdict data yet</div></div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", maxHeight: 220, overflow: "auto" }}>
      {points.map((point, idx) => (
        <div key={`${point.day}-${point.verdict}-${idx}`}
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
          <span className="text-sm font-mono">{new Date(point.day).toLocaleDateString()}</span>
          <span className={`badge ${verdictClass[point.verdict] ?? "badge-draft"}`}>{point.verdict}</span>
          <span style={{ color: "var(--text)", fontWeight: 600, marginLeft: "auto" }}>{point.count}</span>
        </div>
      ))}
    </div>
  );
}
