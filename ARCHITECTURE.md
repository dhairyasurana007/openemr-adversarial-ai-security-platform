# ARCHITECTURE.md — AgentForge Adversarial AI Security Platform

## Summary

AgentForge is a multi-agent adversarial evaluation platform purpose-built to continuously stress-test the OpenEMR Clinical Co-Pilot. Its primary audience is the Red Team Operator who runs campaigns, tunes agents, and acts on findings — with a secondary audience in the Security Lead / CISO who needs governance-grade visibility and a human approval gate on critical disclosures.

The platform is organized around four autonomous agents: an **Orchestrator** that reads system state and decides what to attack next, a **Red Team Agent** that generates and mutates adversarial inputs against the live target, a **Judge Agent** that independently evaluates whether each attack succeeded, and a **Documentation Agent** that converts confirmed exploits into structured vulnerability reports. No agent does two of these jobs. The separation is architectural, not a matter of configuration — an agent that both generates attacks and evaluates them has a conflict of interest by design.

All agent state, attack records, verdicts, and vulnerability reports are persisted in a central Postgres store. This is the substrate the Orchestrator reads to prioritize the next campaign, and the substrate the operator reads to understand what the platform did overnight. The observability layer is not a reporting afterthought — it is the data model the whole system is designed around.

Agent coordination runs on **LangGraph**, chosen for its stateful graph execution, conditional routing, and native support for human-in-the-loop interrupt points. Agents communicate via a **Redis Streams** message queue with typed, schema-validated payloads. No agent calls another directly. Human approval gates sit at two explicit points: before a CRITICAL-severity report is filed, and before any remediation action touches the live target.

Model selection is heterogeneous by design. The Red Team Agent runs on a low-refusal open-source model (Mistral-7B via Ollama) so it is not blocked by the same safety filters it is trying to probe. The Judge Agent runs on a separate frontier model family (GPT-4o) to prevent systematic agreement bias. The Orchestrator and Documentation Agent run on Claude Sonnet, where structured reasoning and JSON output quality matter more than cost-per-token. All choices are revisited at scale breakpoints documented in the cost analysis.

The regression harness converts every confirmed exploit into a deterministic, versioned pytest test that re-runs against every new deployment. A test passes only when the Judge returns FAILURE with high confidence on the exact attack sequence — not because the model's behavior happened to change. Deployment is containerized via Docker Compose for local development and Kubernetes for production, with the adversarial platform and target system running in isolated namespaces.

---

## Assumptions

1. **The target URL is known.** The Red Team Operator has been provided the URL of the OpenEMR Clinical Co-Pilot instance before any campaign is configured. This URL is registered in the platform at setup time and enforced by the Red Team Agent's traffic proxy — the agent cannot fire attacks against any other target.

2. **The operator is legally authorized to perform adversarial testing against the target.** AgentForge assumes the Red Team Operator has a signed engagement agreement with the hospital or organization that owns the OpenEMR Clinical Co-Pilot instance. The platform takes no responsibility for verifying authorization. Running AgentForge against a system without explicit written permission from its owner is unauthorized access and may violate the Computer Fraud and Abuse Act (CFAA) or equivalent laws in the operator's jurisdiction.

---

## Repository Structure

```
agentforge/
├── agents/
│   ├── orchestrator/
│   │   ├── agent.py          # LangGraph node: reads state, emits campaign directives
│   │   ├── prioritizer.py    # Coverage gap scoring, cost throttle logic
│   │   └── prompts/
│   ├── red_team/
│   │   ├── agent.py          # Attack generation + multi-turn sequencing
│   │   ├── mutator.py        # Variant generation from partial successes
│   │   ├── proxy.py          # mitmproxy addon: logs + rate-limits target traffic
│   │   └── prompts/
│   ├── judge/
│   │   ├── agent.py          # Independent verdict evaluation
│   │   ├── rubric.py         # Versioned evaluation criteria per attack category
│   │   ├── ground_truth/     # Labeled dataset for Judge accuracy validation
│   │   └── prompts/
│   └── documentation/
│       ├── agent.py          # Converts confirmed exploits to vuln reports
│       ├── templates/        # Report format per severity
│       └── prompts/
├── orchestration/
│   ├── graph.py              # LangGraph agent graph definition
│   ├── queue.py              # Redis Streams producer/consumer wrappers
│   └── messages.py           # Typed message schemas (Pydantic)
├── state/
│   ├── db.py                 # Postgres connection + ORM models
│   ├── migrations/           # Alembic migrations
│   └── models/
│       ├── attack.py         # Attack execution records
│       ├── verdict.py        # Judge verdicts
│       ├── vulnerability.py  # Confirmed vuln reports
│       └── coverage.py       # Coverage map per attack category
├── regression/
│   ├── harness.py            # Pytest runner triggered by Orchestrator
│   ├── suite/                # Auto-generated regression test files
│   └── reporter.py           # Pass/fail/regression diff reporting
├── observability/
│   ├── dashboard.py          # Streamlit dashboard
│   ├── queries.py            # Canned Postgres queries for key metrics
│   └── cost_tracker.py       # Per-agent token usage accounting
├── workbench/
│   ├── app.py                # Streamlit Attack Workbench (operator UI)
│   ├── attack_builder.py     # Multi-turn sequence editor + live fire
│   ├── campaign_config.py    # Category, mutation depth, cost cap form
│   ├── seed_manager.py       # Create / edit / promote seed cases to evals/
│   └── replay.py             # Load + re-run any past attack from state store
├── target/                   # OpenEMR Clinical Co-Pilot (submodule or fork)
│   └── ...
├── evals/                    # Seed adversarial test cases (human-authored)
│   ├── prompt_injection/
│   ├── phi_exfiltration/
│   ├── state_corruption/
│   ├── tool_misuse/
│   └── results/
├── target_config/            # Operator-supplied target context (testing mode inputs)
│   ├── whitebox/             # Co-Pilot LLM prompts supplied by operator (not committed to repo)
│   └── schema.py             # TargetContext Pydantic model ingested at campaign start
├── taxonomy/                 # Normalized attack technique knowledge base
│   ├── ingest/
│   │   ├── atlas.py          # Ingests MITRE ATLAS techniques via API
│   │   ├── garak.py          # Parses Garak probe definitions
│   │   ├── harmbench.py      # Ingests HarmBench adversarial behavior catalog
│   │   └── jailbreakbench.py # Ingests JailbreakBench attack patterns
│   ├── normalize.py          # Maps all sources to shared TechniqueRecord schema
│   ├── healthcare.py         # Healthcare-specific threat intel (HHS OCR, CHAI)
│   └── refresh.py            # Scheduled re-ingestion + deduplication job
├── vulnerability_reports/    # Filed vuln reports (auto-generated + human-approved)
├── THREAT_MODEL.md
├── ARCHITECTURE.md
├── USERS.md
├── docker-compose.yml        # Local dev: all services
├── k8s/                      # Kubernetes manifests for production
│   ├── agentforge/
│   └── target/
├── .env.example
└── README.md
```

---

## Agent Roles

### Orchestrator Agent
**Responsibility:** Strategic coordinator. Reads system state and decides what the Red Team Agent targets next. Does not generate or evaluate attacks.

**Inputs:** Coverage map, open findings by severity/category, recent Judge verdicts, cost burn rate, deployment change events.

**Outputs:** Campaign directives (target category, seed cases, mutation depth, cost cap), regression run triggers, escalation signals to Documentation Agent, human approval requests for CRITICAL findings.

**Model:** Claude Sonnet — structured reasoning over an evolving state snapshot, JSON directive output.

**Trust level:** High. Only agent that can trigger regression runs and initiate human approval flows.

---

### Red Team Agent
**Responsibility:** Attack generation, mutation, and execution against the live target. Does not evaluate its own results.

**Inputs:** Campaign directive from Orchestrator, historical attack outcomes, threat model definitions, taxonomy records for the target category.

**Outputs:** Attack execution records (prompt sequence, target response, token cost), mutation proposals for partial successes, anomaly escalation flags.

**Model:** Mistral-7B-Instruct via Ollama (local) — low refusal rate on offensive security content, no rate limits, low cost. Fallback to Claude with scoped system prompt for complex multi-turn sequences.

**Trust level:** Low. Operates in an isolated execution context. All traffic to the target is proxied, logged, and rate-limited. Cannot read vulnerability reports or modify the regression suite.

**Attack sources — the taxonomy:**

The Red Team Agent does not generate attacks from scratch. At the start of each campaign it is seeded with relevant technique records from the `taxonomy/` knowledge base, which is built from four public sources ingested and normalized at setup time:

| Source | What it provides | How it's used |
|---|---|---|
| MITRE ATLAS | Authoritative AI/ML adversarial technique taxonomy with case studies and mitigations | Primary category structure; technique descriptions become generation prompts |
| Garak | Open-source LLM probe library with dozens of attack categories and working probe definitions | Probe patterns used as structural templates for Clinical Co-Pilot variants |
| HarmBench | Standardized adversarial behavior catalog with attack methods (GCG, AutoDAN, PAIR, etc.) | Attack methodology reference; method descriptions fed as generation context |
| JailbreakBench | Curated dataset of proven jailbreak patterns with standardized evaluation | Seed payloads for jailbreak and role-bypass categories |

A fifth source, `healthcare.py`, ingests domain-specific threat intelligence: HHS Office for Civil Rights breach incident reports, Coalition for Health AI (CHAI) safety guidelines, and published clinical AI failure case studies. This is the layer that makes the taxonomy relevant to the OpenEMR context specifically — ATLAS and Garak cover the general LLM attack surface; the healthcare layer covers the consequences and patterns that matter when the target handles PHI.

**How sources are used at runtime:**

The taxonomy is ingested once at setup and stored as `TechniqueRecord` rows in Postgres — normalized across all sources, tagged by ATLAS category, deduplication-keyed by technique fingerprint. At campaign time the Orchestrator includes relevant technique IDs in the campaign directive. The Red Team Agent retrieves those records and uses them as *structural context*, not as copy-paste payloads. The model is instructed to generate novel variants that match the technique pattern but are tuned to the Clinical Co-Pilot's specific prompt format, retrieval behavior, and tool surface. Verbatim payloads from public databases are explicitly excluded — they are the least likely to succeed against a target that has seen them before.

Taxonomy records are refreshed on a weekly schedule via `taxonomy/refresh.py`, which pulls updated technique lists from ATLAS and Garak and runs deduplication before writing to the store.

**Mutation strategies:**

When the Judge returns PARTIAL on an attack, the Red Team Agent runs a mutation cycle before the next campaign iteration. Mutation strategies are selected based on the attack category and the partial evidence:

| Strategy | Description | Best for |
|---|---|---|
| PAIR (Prompt Automatic Iterative Refinement) | Agent rewrites the attack based on the target's response, iterating toward a bypass | Single-turn injections; role escalation |
| Semantic rephrasing | Preserves intent, changes wording, register, and framing | Attacks blocked by surface-level pattern matching |
| Indirection wrapping | Embeds the attack inside a plausible clinical context (a note, a form, an uploaded document) | Direct injections that were detected |
| Turn chain extension | Adds preceding turns to build false context before the attack payload | Attacks that need established trust state |
| Encoding variation | Base64, Unicode normalization, leetspeak, instruction splitting across turns | Attacks blocked by string-match filters |
| Persona injection | Introduces a fictional role or authority figure in an earlier turn | Privilege escalation and role bypass |

The mutation depth (how many generation cycles to run) is set by the operator in the Campaign Config and capped by the session cost budget.

**Execution modes:**

The Red Team Agent operates in one of two modes, set per campaign by the operator in the Campaign Config panel. The mode is stored on the campaign directive and enforced by the LangGraph node — not by the agent's own judgment.

*Auto mode* is the default for unattended campaigns (overnight runs, regression sweeps, high-volume exploration). The agent generates attacks, fires them, and hands results to the Judge without any pause. The operator reviews findings after the fact via the observability dashboard. There are no interrupts between attack generation and execution. This mode maximizes throughput and is appropriate when the operator trusts the campaign scope and has set a cost cap.

*Permissions mode* introduces a human approval step between attack generation and execution. After generating each attack sequence — but before firing it against the live target — the agent emits a `HUMAN_APPROVAL_REQUEST` message containing the full proposed sequence, the technique it was derived from, the target category, and the severity estimate. The LangGraph graph parks the run at an interrupt node and surfaces the request in the Attack Workbench approval queue. The operator can:

- **Approve** — attack fires as proposed
- **Edit then approve** — operator modifies the sequence in the Workbench before it fires; edits are logged alongside the original proposal
- **Reject** — attack is discarded; the agent notes the rejection and avoids generating structurally similar variants in the same session
- **Escalate mutation depth** — approve and instruct the agent to generate deeper variants of this specific attack before moving on

Permissions mode is appropriate when the operator wants fine-grained control over what reaches the target — for example, when testing a sensitive category like PHI exfiltration against a near-production system, or when onboarding a new attack category for the first time and the operator wants to validate that the agent's generation is on-target before letting it run freely.

The mode can be changed mid-session from the Campaign Config panel. Switching from Auto to Permissions mid-run pauses the next attack at the approval queue; switching from Permissions to Auto clears any pending approvals and resumes firing immediately.

| | Auto | Permissions |
|---|---|---|
| Attack generation | Autonomous | Autonomous |
| Pre-fire approval | None | Required — operator approves, edits, or rejects each attack |
| Operator touchpoint | Post-run dashboard review | Per-attack approval queue in Workbench |
| Throughput | High | Lower — gated by operator response time |
| Best for | Overnight runs, regression sweeps, high-volume exploration | Sensitive categories, new attack types, near-production targets |
| Cost predictability | Capped by session budget | Lower actual spend — rejected attacks don't fire |

The mode setting does not affect the Judge Agent, Documentation Agent, or regression harness — those operate identically regardless of how the attack was approved.

**Testing modes:**

Separate from execution mode, the operator sets a *testing mode* per campaign that defines how much internal knowledge about the OpenEMR Clinical Co-Pilot the Red Team Agent is given. This is set once at campaign configuration and cannot be changed mid-run — it defines the fundamental nature of the engagement.

*Whitebox mode* gives the Red Team Agent full visibility into the Co-Pilot's LLM prompts — specifically the complete system prompt, any chained or conditional prompt logic, and any prompt templates used across different workflow contexts (intake, chart retrieval, note summarisation, etc.). The operator pastes or uploads these directly into the Campaign Config panel before dispatching. This prompt material is stored encrypted in the `target_config/` table and injected into the Red Team Agent's generation context at campaign time, alongside the taxonomy records for the target attack category.

With the actual prompts in hand, the agent can craft attacks that exploit the exact wording and structure the Co-Pilot uses: targeting specific instruction boundaries, contradicting explicit constraints by name, exploiting known patterns in how the prompt handles role or tool invocation, and generating injections tuned to the Co-Pilot's actual response style. The operator can also review the prompts directly in the Workbench to craft manual attacks informed by what they see. Whitebox finds vulnerabilities that pure probing would never reach, but requires the hospital to share their prompt implementation with the red team operator.

*Blackbox mode* gives the Red Team Agent only the target URL. No prompts, no capability descriptions, no internal context of any kind. The agent interacts with the Co-Pilot exactly as an unauthenticated external attacker would: sending inputs and observing outputs. All attack generation is driven by the taxonomy and mutation strategies alone. The Judge infers expected safe behavior from the attack category definition rather than the actual prompt spec. Blackbox is the most realistic simulation of an external threat actor and requires no disclosure from the hospital, but it is slower to find deep vulnerabilities and will not surface issues that depend on knowledge of the prompt structure.

| | Whitebox | Blackbox |
|---|---|---|
| What the agent receives | Full LLM prompt(s) + target URL | Target URL only |
| What the operator sees | Full prompts visible in Workbench | Inputs and outputs only |
| Attack generation | Targeted to actual prompt wording and structure | Driven by taxonomy patterns and observed responses |
| Judge baseline | Derived from actual prompt constraints | Inferred from attack category definition |
| Discovery depth | Deepest — finds prompt-specific vulnerabilities | Broad — finds behavior-level vulnerabilities |
| Hospital disclosure required | Yes — prompts must be shared with operator | No |
| Simulates | Authorized internal auditor | External attacker with no prior access |

The testing mode is stored on the campaign record and included in every vulnerability report produced by the Documentation Agent. A finding discovered in blackbox mode carries different weight than one discovered in whitebox — a CISO reviewing the report needs to know which context the exploit was found in.

---

### Judge Agent
**Responsibility:** Independent evaluation of attack outcomes against a fixed, versioned rubric. Never shares context with the Red Team Agent.

**Inputs:** Attack execution record (full prompt sequence + target responses), versioned evaluation rubric, expected safe behavior definition.

**Outputs:** Verdict (SUCCESS / PARTIAL / FAILURE / UNCERTAIN), confidence score (0.0–1.0), evidence excerpt, regression flag if a previously-fixed attack now succeeds.

**Model:** GPT-4o — explicitly a different model family from the Red Team Agent to prevent systematic agreement bias.

**Trust level:** Medium. Can write verdicts and set regression flags. Cannot initiate documentation or modify attack records.

**Rubric validation:** A ground-truth dataset of 50 labeled outcomes is re-run against the Judge on every rubric update. Accuracy must exceed 90% before a new rubric version deploys.

---

### Documentation Agent
**Responsibility:** Converts confirmed exploits (Judge verdict: SUCCESS, confidence ≥ 0.85) into structured vulnerability reports. Operates entirely from structured data — no access to raw model outputs or live systems.

**Inputs:** Confirmed exploit record, vulnerability metadata, historical fix data, remediation knowledge base.

**Outputs:** Structured vulnerability report, regression test specification, report status (DRAFT for CRITICAL pending human approval, FILED for HIGH and below).

**Model:** Claude Sonnet — natural language quality and format consistency matter; not on a cost-critical path.

**Trust level:** Low-Medium. Writes to the report table only. CRITICAL reports are held in DRAFT until a human approves.

**Minimum report fields:** unique ID, severity, attack category, affected component, clinical impact, minimal reproducible attack sequence, observed vs. expected behavior, remediation recommendation, fix validation status.

---

## Agent Communication Protocol

Agents communicate via **Redis Streams** (typed message queue). No direct agent-to-agent calls. Each message carries:

```
{
  "source_agent":  "orchestrator" | "red_team" | "judge" | "documentation",
  "target_agent":  "red_team" | "judge" | "documentation" | "human" | "broadcast",
  "message_type":  "CAMPAIGN_DIRECTIVE" | "ATTACK_RESULT" | "JUDGE_VERDICT" |
                   "ESCALATION" | "REGRESSION_FLAG" | "HUMAN_APPROVAL_REQUEST" |
                   "HUMAN_APPROVAL_RESPONSE" | "ATTACK_APPROVAL_REQUEST" |
                   "ATTACK_APPROVAL_RESPONSE",
  "payload":       { ... },   // schema-validated per message_type (Pydantic)
  "session_id":    "uuid",
  "cost_so_far":   0.00       // running token cost for the session
}
```

Malformed or unregistered messages are dead-lettered and logged. Agents consume only the message types they are registered to handle.

---

## Agent Interaction Diagram

*(See rendered diagram below — or refer to `docs/agent-diagram.svg` in the repository.)*

```
                        ┌─────────────────────────────────────────┐
                        │           Postgres State Store           │
                        │  coverage · verdicts · vulns · cost log  │
                        └────────────────┬────────────────────────┘
                                         │ reads
                                         ▼
                        ┌────────────────────────────┐
                        │       Orchestrator Agent    │
                        │   (Claude Sonnet)           │
                        │                             │
                        │  • Prioritizes campaigns    │
                        │  • Triggers regressions     │
                        │  • Manages cost budget      │
                        └───┬──────────┬──────────────┘
                            │          │
              CAMPAIGN_DIRECTIVE    REGRESSION_TRIGGER
                            │          │
                            ▼          ▼
           ┌────────────────────┐  ┌──────────────────────┐
           │  Red Team Agent    │  │  Regression Harness   │
           │  (Mistral-7B /     │  │  (pytest + httpx)     │
           │   Ollama)          │  │                       │
           │                   │  │  Deterministic replay  │
           │  • Generates       │  │  of confirmed exploits│
           │    attacks         │  └──────────┬───────────┘
           │  • Mutates         │             │ REGRESSION_FLAG
           │    partials        │             │
           └────────┬───────────┘             │
                    │                         │
              ATTACK_RESULT                   │
                    │                         │
                    ▼                         ▼
           ┌────────────────────────────────────────┐
           │            Judge Agent                  │
           │            (GPT-4o)                     │
           │                                         │
           │  • Evaluates success / partial / fail   │
           │  • Scores confidence                    │
           │  • Flags regressions                    │
           │  • Escalates UNCERTAIN → human          │
           └────────────────┬────────────────────────┘
                            │
                     JUDGE_VERDICT (SUCCESS, conf ≥ 0.85)
                            │
                            ▼
           ┌────────────────────────────────────────┐
           │        Documentation Agent              │
           │        (Claude Sonnet)                  │
           │                                         │
           │  • Writes structured vuln report        │
           │  • AUTO-FILES: HIGH and below           │
           │  • HOLDS as DRAFT: CRITICAL             │
           └──────────────────┬─────────────────────┘
                              │
              HUMAN_APPROVAL_REQUEST (CRITICAL only)
                              │
                              ▼
                   ┌──────────────────┐
                   │  Human Gate       │
                   │  (Slack / UI)     │
                   │                   │
                   │  Red Team Op      │
                   │  or CISO approves │
                   └──────────────────┘
```

---

## Human Approval Gates

| Gate | Trigger | Who approves | What they decide |
|---|---|---|---|
| CRITICAL report filing | Documentation Agent produces a CRITICAL-severity report | Security Lead / CISO | Approve → report filed; Reject → stays DRAFT, Orchestrator notified |
| Attack pre-fire approval *(Permissions mode only)* | Red Team Agent generates an attack sequence before execution | Red Team Operator | Approve / edit+approve / reject / escalate mutation depth |
| UNCERTAIN verdict review | Judge confidence < 0.7 on HIGH or CRITICAL attack | Red Team Operator | Confirm verdict → finalizes; used to improve rubric |
| Remediation action *(future)* | Agent-proposed patch to live system | Red Team Operator + CISO | Approve / reject before any change touches target |

Approval requests surface via Slack notification with a direct link to the relevant record in the observability dashboard.

---

## Regression & Validation Harness

Every exploit with a Judge verdict of SUCCESS is auto-converted into a regression test entry stored in `regression/suite/`. Rules:

- Stored with the minimal attack sequence, expected safe behavior, and the rubric version used for evaluation
- Tagged with the Clinical Co-Pilot version at time of discovery
- Re-executed against every new deployment, triggered by the Orchestrator
- **Pass condition:** Judge returns FAILURE with confidence ≥ 0.85 on the exact sequence
- **PARTIAL verdict:** flagged as "defense weakened, not resolved" — not a pass
- **Regression on CRITICAL/HIGH:** triggers immediate alert and optional deployment pipeline block

---

## Operator Interface — Attack Workbench

The Attack Workbench (`workbench/app.py`) is a dedicated Streamlit UI for the Red Team Operator to craft, fire, and manage their own attacks independently of the autonomous agent pipeline. It is the primary input surface for the operator — the place where human expertise enters the system.

It runs as a separate service from the observability dashboard, though both read from the same Postgres state store. The Workbench writes to the same `attacks` and `evals` tables the agents use, so manually crafted attacks flow through the Judge and regression harness exactly like agent-generated ones.

### Attack Builder

The core of the Workbench. The operator constructs a multi-turn attack sequence turn by turn, with a live preview of what will be sent to the target. Each turn has a role (user / system / assistant injection) and a prompt body. The operator can:

- Add, reorder, and delete turns in the sequence
- Select the attack category and subcategory from the threat model taxonomy
- Define the expected safe behavior the target should produce
- Set a severity estimate (CRITICAL / HIGH / MEDIUM / LOW) before firing
- Fire the sequence live against the target and see the raw response inline
- Send the result directly to the Judge Agent for an immediate verdict

This bypasses the Orchestrator — the operator is acting as their own campaign director for this attack.

### Campaign Configuration

Before dispatching a campaign to the Orchestrator, the operator sets:

- **Execution mode:** Auto (agent fires attacks autonomously) or Permissions (agent pauses for operator approval before each attack fires)
- **Testing mode:** Whitebox (full LLM prompt visibility) or Blackbox (target URL only). Whitebox unlocks a prompt upload form in the Campaign Config panel. Blackbox shows no additional fields.
- **Target category:** which attack surface to focus on (dropdown from threat model)
- **Seed cases:** which `evals/` entries to use as starting material (multi-select)
- **Mutation depth:** how many variant generations the Red Team Agent should run (1–5)
- **Cost cap:** maximum USD spend for this campaign session
- **Concurrency:** how many parallel attack threads to allow against the target (Permissions mode forces concurrency to 1 — the operator can only review one attack at a time)

The Orchestrator picks these up as a campaign directive rather than computing them autonomously. The operator's configuration takes precedence over the Orchestrator's prioritization logic for that session.

When Permissions mode is active, a live **approval queue** appears in the Workbench sidebar showing all attacks pending review. Each entry shows the proposed sequence, derived technique, category, and severity estimate. The operator works through the queue at their own pace; the agent waits at the LangGraph interrupt node and does not proceed until a response is received or the session times out.

### Seed Manager

The operator can create, edit, and organize seed attack cases without touching the filesystem directly. Each seed case has:

- Attack category and subcategory
- Prompt sequence (one or more turns)
- Expected safe behavior
- Notes on what makes this case interesting or distinct
- Status: DRAFT (not yet used by agents) / ACTIVE (available to Red Team Agent) / RETIRED

Promoting a DRAFT to ACTIVE makes it immediately available to the Red Team Agent's next campaign in that category. Retiring a seed removes it from future campaigns without deleting the historical record.

### Replay

The operator can load any past attack from the state store — whether agent-generated or manually crafted — and re-run it against the current version of the target. Useful for:

- Manually verifying that a patch holds before the full regression suite runs
- Investigating a suspicious PARTIAL verdict by observing the response directly
- Reproducing a finding from a different deployment version for comparison

Replay results are written back to the state store as a new attack record tagged with the current target version, so they count toward coverage and can be re-evaluated by the Judge.

---

## Observability Layer

The Streamlit dashboard (`observability/dashboard.py`) surfaces the following views, all backed by live Postgres queries:

| View | Key question answered |
|---|---|
| Coverage map | Which attack categories have been tested, and at what depth? |
| Finding status | Open / in-progress / patched / validated, by severity and category |
| Verdict trends | Pass/fail rate over time, per category and per system version |
| Regression history | Which tests passed, which regressed, after each deployment |
| Agent activity log | What did each agent do, in what order, per session? |
| Cost dashboard | Tokens per agent per session; projected monthly cost at current volume |
| UNCERTAIN queue | Judge verdicts awaiting Red Team Operator review |

All events are structured JSON logs written to the `agent_events` table. Every vulnerability finding can be traced back through its judge verdict, attack execution record, and the campaign directive that initiated it — a full provenance chain.

---

## Attack Taxonomy

The `taxonomy/` directory is the Red Team Agent's knowledge base — a normalized, versioned store of adversarial techniques drawn from public security research and ingested into Postgres at setup time. It is the difference between an agent that generates random prompts and one that generates attacks grounded in documented, real-world technique patterns.

### Sources

**MITRE ATLAS** (`taxonomy/ingest/atlas.py`)
The primary structural reference. ATLAS (Adversarial Threat Landscape for Artificial-Intelligence Systems) is MITRE's ATT&CK equivalent for ML systems — it catalogs adversarial techniques, real-world case studies, and mitigations across the full ML attack lifecycle. Each ATLAS technique maps to a tactic (Reconnaissance, ML Attack Staging, Exfiltration, etc.) and includes a description, procedure examples, and references. The Red Team Agent uses ATLAS technique descriptions as generation prompts — instructing the model to produce Clinical Co-Pilot-specific variants of each technique rather than copying procedure examples verbatim.

**Garak** (`taxonomy/ingest/garak.py`)
An open-source LLM vulnerability scanner with a library of probes covering jailbreaks, prompt injection, data leakage, hallucination, malware generation, and more. Garak's probe definitions are structured Python classes — each specifies the attack pattern, expected failure mode, and detection criteria. The ingestor parses these definitions and converts them to `TechniqueRecord` entries, preserving the probe's intent and structural pattern while stripping the literal payloads (which are too well-known to succeed against a monitored target).

**HarmBench** (`taxonomy/ingest/harmbench.py`)
A standardized evaluation benchmark from the Center for AI Safety covering a wide range of adversarial behaviors and attack methods, including GCG (Greedy Coordinate Gradient), AutoDAN, PAIR, and multi-turn variants. HarmBench's value is primarily methodological — it documents *how* attacks are constructed, not just *what* they look like. The ingestor extracts method descriptions and stores them as mutation strategy references available to the Red Team Agent's `mutator.py`.

**JailbreakBench** (`taxonomy/ingest/jailbreakbench.py`)
A curated leaderboard and dataset of jailbreak attempts with standardized success evaluation. Provides a strong signal on which jailbreak *patterns* (not payloads) have historically succeeded against frontier models. Used specifically for seeding the role-bypass and persona-injection mutation strategies.

**Healthcare threat intelligence** (`taxonomy/healthcare.py`)
The layer that makes the taxonomy specific to the Clinical Co-Pilot context. Sources include:
- HHS Office for Civil Rights breach incident reports (publicly available, categorized by breach type)
- Coalition for Health AI (CHAI) safety and assurance standards
- Published clinical AI failure case studies from academic literature
- HIPAA security rule guidance on AI system risks

These are not structured attack databases — they are incident and guidance documents. The ingestor uses an LLM extraction pass to identify attack-relevant patterns (e.g., "unauthorized access via AI assistant misconfiguration") and maps them to ATLAS technique categories. Healthcare records are tagged `source=healthcare` and given elevated priority weighting in the Orchestrator's coverage scoring.

### TechniqueRecord schema

All sources are normalized to a shared schema before writing to the `taxonomy_techniques` table:

```python
class TechniqueRecord(BaseModel):
    id: str                     # e.g. "ATLAS.T0051", "garak.probe.dan", "hb.gcg"
    source: str                 # "atlas" | "garak" | "harmbench" | "jailbreakbench" | "healthcare"
    atlas_tactic: str           # ATLAS tactic mapping (best-fit if source is not ATLAS)
    category: str               # AgentForge attack category (e.g. "prompt_injection.indirect")
    name: str
    description: str            # Used as generation context for the Red Team Agent
    technique_pattern: str      # Structural pattern summary — what makes this technique work
    mutation_strategies: list[str]  # Which mutator strategies are applicable
    healthcare_relevance: str   # Why this matters for Clinical Co-Pilot specifically
    severity_prior: str         # CRITICAL | HIGH | MEDIUM | LOW — baseline before Judge evaluation
    last_ingested: datetime
    source_url: str
```

### Refresh cycle

`taxonomy/refresh.py` runs on a weekly schedule (Kubernetes CronJob in production). It pulls updated technique lists from ATLAS and Garak, runs a fingerprint-based deduplication pass, and writes new or updated records to the store. Techniques that no longer appear in the upstream source are marked `deprecated=True` rather than deleted, so historical attack records that reference them retain their provenance.

The Red Team Operator can also trigger a manual refresh from the Campaign Config panel in the Attack Workbench, which is useful after a major ATLAS update or a new Garak release.

---

## Where AI Is Used vs. Deterministic Tooling

| Function | Approach | Justification |
|---|---|---|
| Attack generation & mutation | LLM (Red Team Agent) | Novel, context-sensitive attacks require generative reasoning; static payloads go stale |
| Multi-turn attack sequencing | LLM (Red Team Agent) | Stateful reasoning across conversation turns is generative |
| Verdict evaluation | LLM (Judge Agent) | Semantic understanding of natural language responses required |
| Regression test execution | Deterministic (pytest + httpx) | Replay of known exploits must be reproducible with zero variance |
| Coverage prioritization | LLM (Orchestrator) | Strategic planning over an evolving state snapshot |
| Report generation | LLM (Documentation Agent) | Structured natural language output from structured data |
| Input fuzzing | Traditional fuzzer (Radamsa) | Byte/schema-level fuzzing is faster and more exhaustive than LLM |
| Token cost accounting | Deterministic | Math problem — no LLM involvement |
| Agent state transitions | LangGraph (deterministic graph) | State machine transitions must be auditable and reproducible |
| Taxonomy ingestion | LLM extraction pass (healthcare source) + deterministic parsing (ATLAS, Garak, HarmBench) | Structured sources parsed deterministically; unstructured incident reports need LLM extraction |

---

## Deployment

### Local Development

All services run via Docker Compose. The adversarial platform and the Clinical Co-Pilot target run in separate containers on the same network, with the Red Team Agent's traffic routed through the mitmproxy addon.

```bash
cp .env.example .env          # fill in API keys, DB credentials
docker compose up --build     # starts: postgres, redis, ollama, agentforge, target, dashboard
```

**Services started:**

| Service | Port | Description |
|---|---|---|
| `target` | 8080 | OpenEMR Clinical Co-Pilot |
| `agentforge` | 8000 | Platform API + LangGraph runner |
| `dashboard` | 8501 | Streamlit observability dashboard |
| `postgres` | 5432 | State store |
| `redis` | 6379 | Message queue (Redis Streams) |
| `ollama` | 11434 | Local Mistral-7B inference |
| `proxy` | 8888 | mitmproxy traffic logger |
| `workbench` | 8502 | Attack Workbench operator UI |

### Production (Kubernetes)

Production runs on Kubernetes with the platform and target in isolated namespaces. The Red Team Agent cannot reach any service outside the registered target namespace.

```
k8s/
├── agentforge/
│   ├── deployment.yaml       # agentforge API + LangGraph workers
│   ├── dashboard.yaml        # Streamlit observability
│   ├── workbench.yaml        # Attack Workbench operator UI
│   ├── proxy.yaml            # mitmproxy sidecar
│   └── secrets.yaml          # API keys (sealed secrets)
└── target/
    ├── deployment.yaml       # Clinical Co-Pilot
    └── service.yaml
```

**Key production constraints:**

- Red Team Agent network policy: egress allowed only to `target` namespace service
- Ollama runs as a separate deployment with GPU node selector (optional; falls back to CPU)
- Postgres uses a managed instance (RDS / Cloud SQL) in production; `migrations/` applied via init job on deploy
- Regression harness triggered via Kubernetes Job, not a long-running pod
- Slack webhook secret injected at runtime for human approval gate notifications

### Environment Variables

```bash
# Target
TARGET_URL=https://your-clinical-copilot.example.com

# Models
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
OLLAMA_BASE_URL=http://ollama:11434

# Infrastructure
DATABASE_URL=postgresql://user:pass@postgres:5432/agentforge
REDIS_URL=redis://redis:6379

# Human approval gate
SLACK_WEBHOOK_URL=...
APPROVAL_CHANNEL=#agentforge-approvals

# Cost controls
SESSION_COST_CAP_USD=5.00
DAILY_COST_CAP_USD=50.00
```

---

## Cost Model

| Scale | Est. monthly cost | Dominant driver | Architecture change needed |
|---|---|---|---|
| 100 runs | ~$5–15 | Frontier model calls (Judge, Orchestrator, Docs) | None |
| 1K runs | ~$50–150 | Same; Ollama absorbs Red Team cost | None |
| 10K runs | ~$400–900 | Judge Agent at scale | Move Judge to fine-tuned local model with rubric baked in |
| 100K runs | ~$2K–6K | All frontier calls | Full local inference stack; frontier for orchestration only |

Actual dev spend and detailed per-agent projections are in `COST_ANALYSIS.md`.

---

## Known Tradeoffs

**Red Team model refusal risk.** Even carefully prompted frontier models occasionally refuse to generate offensive content. Mitigation: Mistral-7B via Ollama as the primary Red Team model; it has no refusal training for security research content. The fallback to Claude uses a tightly scoped system prompt that keeps the agent within the registered target surface.

**Judge drift over time.** As the Clinical Co-Pilot evolves, the Judge's rubric can silently become misaligned with actual system behavior. Mitigation: versioned rubric stored in the state store, ground-truth eval set re-run on every rubric change, and a dashboard alert if the Judge's success rate deviates more than 15 percentage points from its 30-day baseline.

**False positives waste engineering time.** A Documentation Agent that confidently files incorrect reports erodes trust in the platform. Mitigation: the 0.85 confidence threshold before auto-filing, UNCERTAIN escalation to the Red Team Operator, and the CRITICAL hold-for-approval gate.

**Autonomous overnight runs are hard to audit.** Mitigation: every agent action is a structured log entry with a session ID, enabling full replay of any run from the `agent_events` table.

**Local Ollama is slow on CPU.** GPU-accelerated inference is strongly recommended for Red Team Agent throughput above ~100 attacks/hour. Fallback to frontier API at cost if GPU is unavailable.
