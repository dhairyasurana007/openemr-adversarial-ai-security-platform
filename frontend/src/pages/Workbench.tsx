import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchAgentLog } from "../api/service";
import { AttackBuilder } from "../components/AttackBuilder";
import { CampaignConfig } from "../components/CampaignConfig";
import { SeedManager } from "../components/SeedManager";
import { TargetInteractionPanel } from "../components/TargetInteractionPanel";
import { useApprovals } from "../hooks/useApprovals";
import { useWebSocket } from "../hooks/useWebSocket";

const tabs = ["Attack Builder", "Campaign Config", "Seed Manager", "Replay"] as const;
type TabName = (typeof tabs)[number];

export default function Workbench() {
  const [activeTab, setActiveTab] = useState<TabName>("Attack Builder");
  const [query, setQuery] = useState("");
  const approvals = useApprovals();
  const log = useQuery({ queryKey: ["agent-log"], queryFn: fetchAgentLog });

  const token = localStorage.getItem("agentforge_token") ?? "";
  const sessionId = localStorage.getItem("agentforge_session_id") ?? "";
  const targetUrl = localStorage.getItem("agentforge_target_url") ?? (__TARGET_ENDPOINT__ || "Not configured");

  useWebSocket({
    sessionId,
    token,
    enabled: Boolean(token && sessionId),
    onEvent: () => {
      void approvals.queue.refetch();
      void log.refetch();
    },
  });

  const pendingApprovals = approvals.queue.data ?? [];

  return (
    <>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div className="page-title">Workbench</div>
          <div className="page-subtitle">Craft and dispatch adversarial attack campaigns</div>
        </div>
        {pendingApprovals.length > 0 && (
          <span className="badge badge-uncertain">{pendingApprovals.length} pending approval{pendingApprovals.length !== 1 ? "s" : ""}</span>
        )}
      </div>

      <div className="tabs">
        {tabs.map((tab) => (
          <button key={tab} type="button" className={`tab${activeTab === tab ? " active" : ""}`} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Attack Builder" && (
        <>
          <AttackBuilder />
          <TargetInteractionPanel events={log.data ?? []} targetUrl={targetUrl} />
        </>
      )}
      {activeTab === "Campaign Config" && <CampaignConfig />}
      {activeTab === "Seed Manager" && <SeedManager />}
      {activeTab === "Replay" && (
        <div className="card">
          <div className="card-title">Replay Attack</div>
          <div className="form-group mt-1">
            <label className="form-label">Attack ID or Category</label>
            <input className="form-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. T01-001 or prompt_injection" />
          </div>
          <button type="button" className="btn btn-primary mt-2">Replay</button>
          {query && <p className="text-muted mt-1">Query: <span className="font-mono">{query}</span></p>}
        </div>
      )}

      {pendingApprovals.length > 0 && (
        <div className="card mt-3">
          <div className="card-title">Approval Queue</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.5rem" }}>
            {pendingApprovals.map((item) => (
              <div key={item.attack_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", padding: "0.6rem 0.75rem", background: "var(--surface)", borderRadius: "var(--radius)", border: "1px solid var(--border)" }}>
                <div>
                  <span className="font-mono" style={{ color: "var(--text)" }}>{item.attack_id.slice(0, 8)}…</span>
                  <span className="text-muted" style={{ marginLeft: "0.75rem" }}>{item.target_category}</span>
                </div>
                <div className="flex gap-1">
                  <span className={`badge badge-${item.severity_estimate.toLowerCase()}`}>{item.severity_estimate}</span>
                  <button type="button" className="btn btn-success btn-xs"
                    onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "approve" })}>
                    Approve
                  </button>
                  <button type="button" className="btn btn-ghost btn-xs"
                    onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "edit_approve" })}>
                    Edit
                  </button>
                  <button type="button" className="btn btn-danger btn-xs"
                    onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "reject" })}>
                    Reject
                  </button>
                  <button type="button" className="btn btn-ghost btn-xs"
                    onClick={() => approvals.attackDecision.mutate({ attackId: item.attack_id, decision: "escalate_mutation" })}>
                    Escalate
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
