# USERS.md — AgentForge Adversarial AI Security Platform

## Overview

The primary user of AgentForge is the Red Team Operator — the security engineer who runs adversarial campaigns, tunes agent behavior, and acts on confirmed findings. Every architectural decision in this platform traces back to their workflow first. The secondary user is the Security Lead / CISO, who interacts with the platform's outputs to maintain governance and approve critical findings, but does not operate the platform directly.

Automation is justified because the threat surface evolves faster than any manual process can keep pace with. The Red Team Operator's job is not to write prompts all day. It is to direct an autonomous system that does, validate that the system is producing quality signal, and escalate findings that require human action. The platform multiplies their capacity; it does not replace their judgment.

---

## Primary User: Red Team Operator (AI Security Engineer)

**Who they are:** A security engineer with a background in application security, ML security, or adversarial AI research. They are responsible for the continuous security posture of the Clinical Co-Pilot — not as a one-time auditor, but as an ongoing operator. They may work alone or lead a small internal red team. They are the person the platform was built for, and the person who would be blamed if a serious vulnerability reached production undetected.

**Goals:**
- Maintain continuous coverage across all known attack categories, not just the ones that were tested last quarter
- Find vulnerabilities before real attackers do, including mutations and variants that weren't in the original test suite
- Convert every confirmed exploit into a regression test so fixes are validated permanently, not just once
- Operate at a scale and speed that manual red teaming cannot achieve
- Produce findings that are credible, reproducible, and actionable — not just interesting

**Pain points without the platform:**
- Manual prompt crafting is slow, inconsistent, and impossible to scale across all attack surfaces simultaneously
- Successful exploits get documented once in a notes file and never systematically re-tested
- There is no reliable way to know whether a patch actually fixed a vulnerability or just changed the model's behavior temporarily
- Coverage is invisible: no one knows which attack categories have been exercised recently and which haven't been touched in months
- After a model update or prompt change, re-validating the full attack surface requires starting from scratch

**Primary workflows:**

*Campaign management:* The Red Team Operator defines which attack categories to prioritize, seeds initial test cases, sets mutation depth and cost caps, and dispatches campaigns to the Red Team Agent. They do not write every variant — the agent handles that. They review the Orchestrator's prioritization decisions and override them when they have context the system doesn't (e.g., a new CVE or an architectural change that opens a new surface).

*Finding review:* After each campaign cycle, the operator reviews Judge verdicts, confirms or disputes UNCERTAIN outcomes, and promotes high-confidence findings to the Documentation Agent for formal reporting. They are the quality gate between raw attack output and the engineering queue.

*Regression monitoring:* After a platform engineer deploys a patch, the operator triggers or reviews the regression run to confirm the fix held. When a previously-patched vulnerability reappears, they are the first to be notified and the one who determines whether it's a true regression or a rubric drift.

*Platform tuning:* The operator seeds new attack categories as the threat landscape evolves, adjusts Judge rubric criteria when they drift, and manages cost budgets across agent sessions. They are responsible for the health of the platform itself, not just its outputs.

**Why automation is the right solution:**
A skilled engineer can craft 20–50 adversarial prompts in a day. The platform generates and evaluates thousands, including mutations of partially-successful attacks the operator would never have time to try manually. More importantly, automation is the only way to guarantee that every known exploit is re-run against every new version of the target — a guarantee no manual process can make. The operator's value is not in prompt execution; it is in strategy, judgment, and escalation. The platform handles the execution so they can focus on what only a human can do.

**Key use cases:**

- *New deployment triggered:* The Orchestrator detects a new version of the Clinical Co-Pilot. The operator reviews the auto-triggered regression run, confirms no regressions, and approves the coverage report for the release sign-off.
- *Coverage gap identified:* The operator notices the observability dashboard shows zero test cases in the "indirect prompt injection via uploaded documents" subcategory. They seed three example cases and dispatch a campaign; the Red Team Agent generates 40 variants overnight.
- *Partial success escalation:* An attack returns a PARTIAL verdict. The operator reviews the evidence, determines it's worth pursuing, and instructs the Red Team Agent to run a deep mutation cycle targeting that specific bypass pattern.
- *Overnight audit:* The operator reviews the session log for an unattended overnight run: which agents ran, in what order, what did each one cost, and did any produce anomalous output outside the intended attack scope.
- *Judge drift suspected:* The operator notices the Judge's success rate has climbed from 12% to 34% over two weeks without a corresponding increase in actual vulnerabilities. They pull the ground-truth eval set, re-run it against the current rubric, and identify a drift in the PHI exfiltration evaluation criteria.

---

---

---

## Secondary User: Security Lead / CISO (Oversight & Governance)

**Who they are:** The senior security stakeholder — either the organization's CISO or a security lead overseeing AI safety for the OpenEMR deployment. They are not in the day-to-day tooling but need confidence that the platform is producing trustworthy, audit-ready output.

**Primary workflows:**
- Reviewing high-level coverage and resilience trends over time
- Approving or escalating critical-severity vulnerability reports before they are filed or disclosed
- Reviewing AI cost spend and confirming it scales responsibly
- Signing off on the platform's trust boundaries: which agent actions are autonomous, which require human approval

**Why automation is the right solution:**
A CISO cannot rely on point-in-time penetration tests for a system that evolves continuously. The platform provides a continuous, observable, and auditable record of the system's security posture — not a snapshot. The human approval gate before critical-severity reports are filed ensures the CISO retains control over disclosure and remediation prioritization without being a bottleneck for routine findings. The observability layer gives them the trend data needed to answer regulators, auditors, and clinical leadership with evidence rather than assertion.

**Key use cases:**
- View dashboard: is the Clinical Co-Pilot more or less resilient than it was 30 days ago?
- Approve a CRITICAL severity finding before the Documentation Agent files it for engineering action
- Review a cost report: what did last week's adversarial campaign cost, and what is the projected cost at 10K runs/month?
- Export an audit-ready summary of all confirmed vulnerabilities, their status, and validation results

---

## Summary Table

| User | Role | Primary Need | Automation Justification | Human-in-the-Loop Requirement |
|---|---|---|---|---|
| **Red Team Operator** | **Primary** | Continuous, scalable adversarial coverage with full platform control | Manual testing cannot match mutation depth, regression consistency, or coverage breadth | Campaign strategy; Judge verdict disputes; platform tuning |
| Security Lead / CISO | Secondary | Audit-ready trend data + governance over critical findings | Point-in-time tests cannot track a continuously evolving system | Approving CRITICAL-severity findings before filing |
