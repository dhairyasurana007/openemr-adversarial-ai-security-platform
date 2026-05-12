# AgentForge — Adversarial Eval Suite

Seed test cases for the OpenEMR Clinical Co-Pilot red-team platform.
Derived from [`THREAT_MODEL.md`](../THREAT_MODEL.md).

## Structure

```
evals/
├── seed/                   Seed YAML test case suites (one file per threat)
│   ├── T01_direct_prompt_injection.yaml
│   ├── T02_caller_context_bypass.yaml       ← CRITICAL
│   ├── T03_indirect_injection_ehr.yaml
│   ├── T04_document_injection.yaml
│   ├── T07_phi_leakage_openrouter.yaml      ← CRITICAL
│   ├── T09_tool_parameter_tampering.yaml
│   ├── T10_unintended_tool_invocation.yaml
│   ├── T12_token_exhaustion.yaml
│   ├── T15_persona_hijacking.yaml
│   └── T17_audit_trail_spoofing.yaml
├── results/                Runner outputs (gitignored — contains PHI from test runs)
├── schemas.py              Pydantic models for CaseSuite, AttackCase, CaseResult
├── runner.py               Standalone test executor
├── regression_suite.json   IDs of cases that must pass on every build
└── README.md               This file
```

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your target URL, session cookie, and patient UUIDs

# 3. Run a single suite
python -m evals.runner --suite evals/seed/T02_caller_context_bypass.yaml

# 4. Run the full regression suite
python -m evals.runner --regression

# 5. Run the Red Team Agent (full autonomous campaign)
python agentforge-adversarial-ai-security-platform/agents/red_team_agent.py
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `TARGET_BASE_URL` | Yes | OpenEMR base URL, e.g. `http://localhost:80` |
| `SESSION_COOKIE` | Yes | Authenticated PHP session cookie value |
| `CSRF_TOKEN` | Yes | CSRF token for the authenticated session |
| `SESSION_PATIENT_UUID` | Yes | UUID of the session-bound patient |
| `VICTIM_UUID` | Yes | UUID of a second patient (cross-patient tests) |
| `ANTHROPIC_API_KEY` | Yes | For LLM-judge evaluation in Red Team Agent |
| `RED_TEAM_SUITE` | No | Comma-separated threat IDs to run (e.g. `T01,T02`) |
| `RED_TEAM_MAX_VARIANTS` | No | Max variants per confirmed failure (default: 3) |

## Case severity summary

| Threat | Cases | Severity | Regression |
|--------|-------|----------|------------|
| T02 CALLER_CONTEXT bypass | 5 | **Critical** | Yes |
| T07 PHI → OpenRouter | 3 | **Critical** | Yes |
| T01 Direct prompt injection | 4 | High | Yes |
| T03 Indirect EHR injection | 4 | High | Yes |
| T09 Tool param tampering | 4 | High | Yes |
| T10 Unintended tool invocation | 4 | High | Yes |
| T17 Audit trail spoofing | 3 | High | Yes |
| T04 Document injection | 3 | High | Yes |
| T15 Persona hijacking | 3 | Medium | Yes |
| T12 Token exhaustion | 2 | Medium | No |

## Verdict semantics

| Verdict | Meaning |
|---------|---------|
| `FAIL` | Attack succeeded — vulnerability confirmed |
| `PASS` | Attack failed — system defended correctly |
| `PARTIAL` | Ambiguous — requires human review |
| `ERROR` | Test infrastructure error (target unreachable) |

`FAIL` cases are automatically added to `regression_suite.json` and will be
re-run on every subsequent build.

## Adding new cases

1. Add a case block to the appropriate YAML in `evals/seed/`
2. Follow the schema in `schemas.py` (especially `fail_if` detection rules)
3. Run the suite to confirm the case executes
4. If the case confirms a new vulnerability, it will be auto-added to regression

## Manual cases

Cases marked with `SETUP REQUIRED` need EHR data pre-population (e.g., injected
clinical notes). See the `preconditions` field in each case for setup steps.
The runner will execute the HTTP trigger; manual inspection of the DB or network
proxy is then needed to confirm the verdict.
