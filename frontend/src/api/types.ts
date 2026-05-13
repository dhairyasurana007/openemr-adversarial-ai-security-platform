export interface Campaign {
  id: string;
  session_id: string;
  execution_mode: "auto" | "permissions";
  testing_mode: "whitebox" | "blackbox";
  target_category: string;
  target_url?: string;
  status: string;
  cost_so_far_usd: number;
}

export interface CampaignCreateResponse {
  id: string;
  session_id: string;
  status: string;
}

export interface AttackRecord {
  id: string;
  campaign_id: string;
  threat_id: string;
  attack_category: string;
  prompt_sequence: Array<Record<string, unknown>>;
  target_response: string;
  response_status_code: number;
}

export interface Verdict {
  id: string;
  attack_id: string;
  verdict: "SUCCESS" | "PARTIAL" | "FAILURE" | "UNCERTAIN";
  confidence?: number;
  evidence_excerpt?: string;
}

export interface VulnerabilityReport {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "DRAFT" | "FILED" | "PATCHED" | "VALIDATED";
  attack_category: string;
  attack_sequence?: Array<Record<string, unknown>>;
}

export interface CoverageMap {
  attack_category: string;
  threat_model_ref: string;
  total_attacks: number;
  success_count: number;
  partial_count: number;
  failure_count: number;
  residual_risk: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
}

export interface AgentEvent {
  id: string;
  session_id: string;
  agent: string;
  event_type: string;
  payload: Record<string, unknown>;
  cost_delta_usd: number;
  created_at: string;
}

export interface TechniqueRecord {
  id: string;
  source: string;
  category: string;
  name: string;
  severity_prior: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  deprecated: boolean;
}

export interface HumanApprovalRequest {
  attack_id: string;
  campaign_id: string;
  proposed_sequence: Array<Record<string, unknown>>;
  technique_id: string;
  target_category: string;
  severity_estimate: string;
}
