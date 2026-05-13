import { useQuery } from "@tanstack/react-query";

import { fetchAgentLog } from "../api/service";
import { CoverageMap } from "../components/CoverageMap";
import { VerdictTrend } from "../components/VerdictTrend";
import { useCoverage } from "../hooks/useCoverage";
import { useWebSocket } from "../hooks/useWebSocket";

export default function Dashboard() {
  const { coverage, trends, cost, uncertain } = useCoverage();
  const log = useQuery({ queryKey: ["agent-log"], queryFn: fetchAgentLog });

  const token = localStorage.getItem("agentforge_token") ?? "";
  const sessionId = localStorage.getItem("agentforge_session_id") ?? "";
  const targetUrl = localStorage.getItem("agentforge_target_url") ?? "Not configured";

  useWebSocket({
    sessionId,
    token,
    enabled: Boolean(token && sessionId),
    onEvent: () => { void log.refetch(); },
  });

  const totalCost = cost.data?.total_cost_usd ?? 0;
  const uncertainCount = uncertain.data?.length ?? 0;
  const successCount = (coverage.data ?? []).reduce((s, r) => s + r.success_count, 0);
  const totalAttacks = (coverage.data ?? []).reduce((s, r) => s + r.total_attacks, 0);

  return (
    <>
      <div className="page-header">
        <div className="page-title">Dashboard</div>
        <div className="page-subtitle">Live overview of adversarial campaign activity</div>
        <div className="card-meta" style={{ marginTop: "0.35rem" }}>
          Target Endpoint: <span className="font-mono">{targetUrl}</span>
        </div>
      </div>

      <div className="grid grid-4 mb-2">
        <div className="card">
          <div className="card-title">Total Attacks</div>
          <div className="card-value">{totalAttacks.toLocaleString()}</div>
          <div className="card-meta">across all categories</div>
        </div>
        <div className="card">
          <div className="card-title">Successes</div>
          <div className="card-value" style={{ color: "var(--danger)" }}>{successCount}</div>
          <div className="card-meta">exploits confirmed</div>
        </div>
        <div className="card">
          <div className="card-title">Uncertain Queue</div>
          <div className="card-value" style={{ color: "var(--purple)" }}>{uncertainCount}</div>
          <div className="card-meta">awaiting review</div>
        </div>
        <div className="card">
          <div className="card-title">Total Cost</div>
          <div className="card-value" style={{ color: "var(--warning)" }}>${totalCost.toFixed(2)}</div>
          <div className="card-meta">last 30 days</div>
        </div>
      </div>

      <div className="grid grid-2 mb-2">
        <div className="card">
          <div className="card-title">Coverage Map</div>
          <CoverageMap rows={coverage.data ?? []} />
        </div>
        <div className="card">
          <div className="card-title">Verdict Trends — Last 30 days</div>
          <VerdictTrend points={trends.data ?? []} />
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Cost by Agent</div>
          {(cost.data?.by_agent ?? []).length === 0 ? (
            <div className="empty"><div className="empty-text">No cost data yet</div></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {(cost.data?.by_agent ?? []).map((item) => (
                <div key={item.agent} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
                  <span className="font-mono" style={{ color: "var(--text-secondary)" }}>{item.agent}</span>
                  <span style={{ color: "var(--warning)", fontWeight: 600 }}>${item.cost_usd.toFixed(4)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="card">
          <div className="card-title">Agent Activity Log</div>
          <div style={{ maxHeight: 220, overflow: "auto" }}>
            {(log.data ?? []).length === 0 ? (
              <div className="empty"><div className="empty-text">No activity yet</div></div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                {(log.data ?? []).slice(0, 20).map((e) => (
                  <div key={e.id} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                    <span className="badge badge-filed" style={{ flexShrink: 0 }}>{e.agent}</span>
                    <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{e.event_type}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
