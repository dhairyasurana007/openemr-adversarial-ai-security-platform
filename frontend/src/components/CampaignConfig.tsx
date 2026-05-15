import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { createCampaign } from "../api/service";

interface Props {
  defaultTestingMode?: "blackbox" | "whitebox";
  onLaunched?: () => void;
}

export function CampaignConfig({ defaultTestingMode = "blackbox", onLaunched }: Props = {}) {
  const defaultTargetUrl = __TARGET_ENDPOINT__ || "";
  const [form, setForm] = useState({
    execution_mode: "auto",
    testing_mode: defaultTestingMode,
    target_category: "prompt_injection",
    target_url: defaultTargetUrl,
    seed_case_ids: "T01-001",
    mutation_depth: 2,
    cost_cap_usd: 5,
    concurrency: 1,
  });

  const mutation = useMutation({
    mutationFn: () =>
      createCampaign({
        ...form,
        seed_case_ids: form.seed_case_ids.split(",").map((s) => s.trim()).filter(Boolean),
        technique_ids: [],
        connection_path: "copilot_endpoint",
      }),
    onSuccess: (data) => {
      localStorage.setItem("agentforge_session_id", data.session_id);
      localStorage.setItem("agentforge_campaign_id", data.id);
      localStorage.setItem("agentforge_target_url", form.target_url);
      onLaunched?.();
    },
  });

  return (
    <div className="card">
      <div className="card-title">Campaign Configuration</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "0.75rem" }}>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Execution Mode</label>
            <select className="form-select" value={form.execution_mode}
              onChange={(e) => setForm((s) => ({ ...s, execution_mode: e.target.value }))}>
              <option value="auto">Auto</option>
              <option value="permissions">Permissions</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Testing Mode</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                type="button"
                className={`btn btn-sm ${form.testing_mode === "blackbox" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setForm((s) => ({ ...s, testing_mode: "blackbox" }))}
                aria-pressed={form.testing_mode === "blackbox"}
              >
                {form.testing_mode === "blackbox" ? "✓ " : ""}Blackbox
              </button>
              <button
                type="button"
                className={`btn btn-sm ${form.testing_mode === "whitebox" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setForm((s) => ({ ...s, testing_mode: "whitebox" }))}
                aria-pressed={form.testing_mode === "whitebox"}
              >
                {form.testing_mode === "whitebox" ? "✓ " : ""}Whitebox
              </button>
            </div>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Target Category</label>
          <input className="form-input" value={form.target_category}
            onChange={(e) => setForm((s) => ({ ...s, target_category: e.target.value }))} />
        </div>

        <div className="form-group">
          <label className="form-label">Target Endpoint URL</label>
          <input className="form-input" value={form.target_url}
            placeholder="https://target.example/api"
            onChange={(e) => setForm((s) => ({ ...s, target_url: e.target.value }))} />
        </div>

        <div className="form-group">
          <label className="form-label">Seed Case IDs (comma-separated)</label>
          <input className="form-input" value={form.seed_case_ids}
            placeholder="T01-001, T02-003, …"
            onChange={(e) => setForm((s) => ({ ...s, seed_case_ids: e.target.value }))} />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Mutation Depth — {form.mutation_depth}</label>
            <input type="range" min={1} max={5} value={form.mutation_depth}
              style={{ width: "100%", accentColor: "var(--primary)" }}
              onChange={(e) => setForm((s) => ({ ...s, mutation_depth: Number(e.target.value) }))} />
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              {[1,2,3,4,5].map((n) => <span key={n} className="text-muted text-sm">{n}</span>)}
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Cost Cap (USD)</label>
            <input type="number" className="form-input" min={0.5} max={100} step={0.5} value={form.cost_cap_usd}
              onChange={(e) => setForm((s) => ({ ...s, cost_cap_usd: Number(e.target.value) }))} />
          </div>
        </div>

        <div>
          <button type="button" className="btn btn-primary" onClick={() => mutation.mutate()}
            disabled={mutation.isPending}>
            {mutation.isPending ? "Dispatching…" : "⚡ Dispatch Campaign"}
          </button>
        </div>

        {mutation.isSuccess && (
          <div className="alert alert-success">✓ Campaign dispatched successfully</div>
        )}
        {mutation.isError && (
          <div className="alert alert-danger">✕ Failed to dispatch campaign</div>
        )}
      </div>
    </div>
  );
}
