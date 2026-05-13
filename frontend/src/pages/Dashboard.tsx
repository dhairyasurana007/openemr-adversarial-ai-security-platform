import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

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

  useWebSocket({
    sessionId,
    token,
    enabled: Boolean(token && sessionId),
    onEvent: () => {
      void log.refetch();
    },
  });

  return (
    <section>
      <h2>Dashboard</h2>
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))" }}>
        <article>
          <h3>Coverage Map</h3>
          <CoverageMap rows={coverage.data ?? []} />
        </article>
        <article>
          <h3>Verdict Trends</h3>
          <VerdictTrend points={trends.data ?? []} />
        </article>
        <article>
          <h3>Cost Dashboard</h3>
          <p>Total: ${cost.data?.total_cost_usd?.toFixed(2) ?? "0.00"}</p>
          <ul>
            {(cost.data?.by_agent ?? []).map((item) => (
              <li key={item.agent}>
                {item.agent}: ${item.cost_usd.toFixed(2)}
              </li>
            ))}
          </ul>
        </article>
        <article>
          <h3>Agent Activity Log</h3>
          <div style={{ maxHeight: 180, overflow: "auto", border: "1px solid #ddd", padding: "0.5rem" }}>
            <pre>{JSON.stringify(log.data ?? [], null, 2)}</pre>
          </div>
        </article>
        <article>
          <h3>UNCERTAIN Queue</h3>
          <p>
            <Link to="/workbench">Items: {uncertain.data?.length ?? 0}</Link>
          </p>
        </article>
      </div>
    </section>
  );
}
