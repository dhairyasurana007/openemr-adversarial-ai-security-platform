import { useState } from "react";

import { AttackBuilder } from "../components/AttackBuilder";
import { CampaignConfig } from "../components/CampaignConfig";
import { SeedManager } from "../components/SeedManager";
import { useApprovals } from "../hooks/useApprovals";
import { useWebSocket } from "../hooks/useWebSocket";

const tabs = ["Attack Builder", "Campaign Config", "Seed Manager", "Replay"] as const;
type TabName = (typeof tabs)[number];

export default function Workbench() {
  const [activeTab, setActiveTab] = useState<TabName>("Attack Builder");
  const [query, setQuery] = useState("");
  const approvals = useApprovals();

  const token = localStorage.getItem("agentforge_token") ?? "";
  const sessionId = localStorage.getItem("agentforge_session_id") ?? "";

  useWebSocket({
    sessionId,
    token,
    enabled: Boolean(token && sessionId),
    onEvent: () => {
      void approvals.queue.refetch();
    },
  });

  return (
    <section>
      <h2>Workbench</h2>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {tabs.map((tab) => (
          <button key={tab} type="button" onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>
      {activeTab === "Attack Builder" ? <AttackBuilder /> : null}
      {activeTab === "Campaign Config" ? <CampaignConfig /> : null}
      {activeTab === "Seed Manager" ? <SeedManager /> : null}
      {activeTab === "Replay" ? (
        <section>
          <h3>Replay</h3>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Attack ID or category" />
          <button type="button">Replay</button>
          <p>Query: {query || "(none)"}</p>
        </section>
      ) : null}

      <aside style={{ marginTop: "1rem", borderTop: "1px solid #ddd", paddingTop: "1rem" }}>
        <h3>Approval Queue</h3>
        {(approvals.queue.data ?? []).map((item) => (
          <div key={item.attack_id} style={{ border: "1px solid #ddd", padding: "0.5rem", marginBottom: "0.5rem" }}>
            <p>
              {item.attack_id} | {item.target_category} | {item.severity_estimate}
            </p>
            <button
              type="button"
              onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "approve" })}
            >
              Approve
            </button>
            <button
              type="button"
              onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "edit_approve" })}
            >
              Edit+Approve
            </button>
            <button
              type="button"
              onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "reject" })}
            >
              Reject
            </button>
            <button
              type="button"
              onClick={() =>
                approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "escalate_mutation" })
              }
            >
              Escalate
            </button>
          </div>
        ))}
      </aside>
    </section>
  );
}
