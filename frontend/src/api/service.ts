import api from "./client";
import type {
  AgentEvent,
  CampaignCreateResponse,
  CoverageMap,
  HumanApprovalRequest,
  TechniqueRecord,
  VulnerabilityReport,
} from "./types";

export async function fetchCoverage() {
  const { data } = await api.get<CoverageMap[]>("/observability/coverage");
  return data;
}

export async function fetchTrends() {
  const { data } = await api.get<Array<{ day: string; verdict: string; count: number }>>(
    "/observability/trends",
    { params: { days: 30 } },
  );
  return data;
}

export async function fetchCost() {
  const { data } = await api.get<{ days: number; total_cost_usd: number; by_agent: Array<{ agent: string; cost_usd: number }> }>(
    "/observability/cost",
  );
  return data;
}

export async function fetchAgentLog() {
  const { data } = await api.get<AgentEvent[]>("/observability/agent-log");
  return data;
}

export async function fetchUncertain() {
  const { data } = await api.get<Array<{ id: string }>>("/observability/uncertain");
  return data;
}

export async function createCampaign(payload: Record<string, unknown>) {
  const { data } = await api.post<CampaignCreateResponse>("/campaigns", payload);
  return data;
}

export async function fetchFindings(filters: {
  severity?: string;
  status?: string;
}) {
  const { data } = await api.get<VulnerabilityReport[]>("/vulnerabilities", { params: filters });
  return data;
}

export async function fetchSeeds() {
  const { data } = await api.get<TechniqueRecord[]>("/taxonomy/techniques");
  return data;
}

export async function fetchApprovalQueue() {
  const { data } = await api.get<HumanApprovalRequest[]>("/observability/uncertain");
  return data;
}

export async function decideAttackApproval(attackId: string, decision: string) {
  const { data } = await api.post(`/approvals/attack/${attackId}`, { decision });
  return data;
}

export async function decideReportApproval(reportId: string, decision: string) {
  const { data } = await api.post(`/approvals/report/${reportId}`, { decision });
  return data;
}

export async function fireManualAttack(payload: {
  message: string;
  surface: "chat";
  use_rag: boolean;
  session_id?: string;
  testing_mode?: string;
  attack_category?: string;
}) {
  const { data } = await api.post<{ status_code: number; response: unknown }>("/attacks/manual-fire", payload);
  return data;
}

export async function runTargetHealthCheck(sessionId?: string) {
  return fireManualAttack({
    message: "health_check",
    surface: "chat",
    use_rag: true,
    session_id: sessionId,
  });
}

export async function fetchTargetEndpoint() {
  const { data } = await api.get<{ target_endpoint: string }>("/attacks/target-endpoint");
  return data;
}
