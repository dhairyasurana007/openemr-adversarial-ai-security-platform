import { useFindings } from "../hooks/useFindings";

export default function ApprovalQueue() {
  const findings = useFindings({ severity: "CRITICAL", status: "DRAFT" });

  return (
    <section>
      <h2>CISO Approval Queue</h2>
      {(findings.data ?? []).length === 0 ? <p>No CRITICAL DRAFT reports.</p> : null}
      {(findings.data ?? []).map((item) => (
        <article key={item.id} style={{ border: "1px solid #ddd", marginBottom: "0.5rem", padding: "0.5rem" }}>
          <h3>{item.attack_category}</h3>
          <p>
            {item.severity} | {item.status}
          </p>
          <button type="button">Approve</button>
          <button type="button">Reject</button>
        </article>
      ))}
    </section>
  );
}
