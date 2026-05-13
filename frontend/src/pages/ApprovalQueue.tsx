import { useFindings } from "../hooks/useFindings";

export default function ApprovalQueue() {
  const findings = useFindings({ severity: "CRITICAL", status: "DRAFT" });
  const items = findings.data ?? [];

  return (
    <>
      <div className="page-header">
        <div className="page-title">CISO Approval Queue</div>
        <div className="page-subtitle">Critical findings pending sign-off before filing</div>
      </div>

      {findings.isLoading ? (
        <div className="empty"><div className="empty-text">Loading…</div></div>
      ) : items.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">✓</div>
          <div className="empty-text">No critical reports awaiting approval</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {items.map((item) => (
            <div key={item.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.75rem" }}>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--text)", marginBottom: "4px" }}>{item.attack_category}</div>
                  <span className="font-mono text-muted">{item.id}</span>
                </div>
                <div className="flex gap-1">
                  <span className={`badge badge-${item.severity.toLowerCase()}`}>{item.severity}</span>
                  <span className={`badge badge-${item.status.toLowerCase()}`}>{item.status}</span>
                </div>
              </div>
              <div className="flex gap-1">
                <button type="button" className="btn btn-success btn-sm">✓ Approve</button>
                <button type="button" className="btn btn-danger btn-sm">✕ Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
