import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { createCampaign } from "../api/service";

export function CampaignConfig() {
  const [form, setForm] = useState({
    execution_mode: "auto",
    testing_mode: "blackbox",
    target_category: "prompt_injection",
    seed_case_ids: "T01-001",
    mutation_depth: 2,
    cost_cap_usd: 5,
    concurrency: 1,
  });

  const mutation = useMutation({
    mutationFn: () =>
      createCampaign({
        ...form,
        seed_case_ids: form.seed_case_ids.split(",").map((item) => item.trim()).filter(Boolean),
        technique_ids: [],
        target_url: "http://localhost",
        connection_path: "copilot_endpoint",
      }),
  });

  return (
    <section>
      <h3>Campaign Config</h3>
      <label>
        Execution Mode
        <select
          value={form.execution_mode}
          onChange={(e) => setForm((s) => ({ ...s, execution_mode: e.target.value }))}
        >
          <option value="auto">auto</option>
          <option value="permissions">permissions</option>
        </select>
      </label>
      <label>
        Testing Mode
        <select
          value={form.testing_mode}
          onChange={(e) => setForm((s) => ({ ...s, testing_mode: e.target.value }))}
        >
          <option value="blackbox">blackbox</option>
          <option value="whitebox">whitebox</option>
        </select>
      </label>
      <label>
        Category
        <input
          value={form.target_category}
          onChange={(e) => setForm((s) => ({ ...s, target_category: e.target.value }))}
        />
      </label>
      <label>
        Seed Case IDs (comma-separated)
        <input
          value={form.seed_case_ids}
          onChange={(e) => setForm((s) => ({ ...s, seed_case_ids: e.target.value }))}
        />
      </label>
      <label>
        Mutation Depth
        <input
          type="range"
          min={1}
          max={5}
          value={form.mutation_depth}
          onChange={(e) => setForm((s) => ({ ...s, mutation_depth: Number(e.target.value) }))}
        />
      </label>
      <button type="button" onClick={() => mutation.mutate()}>
        Dispatch Campaign
      </button>
      {mutation.isSuccess ? <p>Campaign dispatched.</p> : null}
    </section>
  );
}
