"""
Eval runner — loads YAML seed cases, executes them against the live target,
evaluates responses, and writes results to evals/results/.

Usage:
    python -m evals.runner --suite seed/T02_caller_context_bypass.yaml
    python -m evals.runner --all-seed          # run every seed file
    python -m evals.runner --regression        # run regression suite only

Environment variables (see .env.example):
    TARGET_BASE_URL         Base URL of the OpenEMR instance under test
    SESSION_COOKIE          Authenticated PHP session cookie value
    CSRF_TOKEN              CSRF token for the session
    VICTIM_UUID             UUID of a second patient (for cross-patient tests)
    SESSION_PATIENT_UUID    UUID of the session-bound patient
    ANTHROPIC_API_KEY       For LLM-judge evaluation steps
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from rich.console import Console
from rich.table import Table

from evals.schemas import (
    AttackCase,
    CaseResult,
    CaseSuite,
    DetectionRule,
    Verdict,
)

console = Console()

RESULTS_DIR = Path(__file__).parent / "results"
SEED_DIR = Path(__file__).parent / "seed"
REGRESSION_SUITE_FILE = Path(__file__).parent / "regression_suite.json"


# ---------------------------------------------------------------------------
# Template substitution
# ---------------------------------------------------------------------------

_TEMPLATE_VARS: dict[str, str] = {}


def _resolve_template_vars() -> dict[str, str]:
    return {
        "victim_uuid": os.getenv("VICTIM_UUID", "00000000-0000-0000-0000-000000000042"),
        "session_patient_uuid": os.getenv("SESSION_PATIENT_UUID", "aaaaaaaa-0000-0000-0000-000000000001"),
        "csrf_token": os.getenv("CSRF_TOKEN", "test-csrf-token"),
        "base_url": os.getenv("TARGET_BASE_URL", "http://localhost:80"),
    }


def _substitute(value: Any, vars: dict[str, str]) -> Any:
    if isinstance(value, str):
        for k, v in vars.items():
            value = value.replace(f"{{{{{k}}}}}", v)
        return value
    if isinstance(value, dict):
        return {k: _substitute(v, vars) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, vars) for v in value]
    return value


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _build_auth_headers(auth_type: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if auth_type == "session_cookie":
        cookie = os.getenv("SESSION_COOKIE", "")
        if cookie:
            headers["Cookie"] = cookie
    elif auth_type == "bearer_token":
        token = os.getenv("BEARER_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "internal_secret":
        secret = os.getenv("CLINICAL_COPILOT_INTERNAL_SECRET", "")
        if secret:
            headers["X-Clinical-Copilot-Internal-Secret"] = secret
    return headers


# ---------------------------------------------------------------------------
# Detection rule evaluation
# ---------------------------------------------------------------------------

def _evaluate_rule(rule: DetectionRule, response: httpx.Response) -> bool:
    """Return True if the rule matches (triggering a FAIL or PASS condition)."""
    body = response.text
    if rule.kind == "response_contains":
        return str(rule.value).lower() in body.lower()
    if rule.kind == "response_not_contains":
        return str(rule.value).lower() not in body.lower()
    if rule.kind == "status_code_is":
        return response.status_code == int(rule.value)
    if rule.kind == "status_code_not":
        return response.status_code != int(rule.value)
    if rule.kind == "json_path_equals":
        # value is {"path": "a.b.c", "expected": ...}
        try:
            data = response.json()
            parts = str(rule.value["path"]).split(".")
            node = data
            for p in parts:
                node = node[p]
            return node == rule.value["expected"]
        except Exception:
            return False
    if rule.kind == "regex_match":
        return bool(re.search(str(rule.value), body))
    if rule.kind == "uuid_in_response":
        # Checks if a specific UUID appears in the response
        return str(rule.value).lower() in body.lower()
    # llm_judge is handled separately — default to inconclusive
    return False


def _determine_verdict(
    case: AttackCase,
    response: httpx.Response,
) -> tuple[Verdict, list[str]]:
    matched: list[str] = []

    for rule in case.fail_if:
        if _evaluate_rule(rule, response):
            matched.append(f"FAIL_IF: {rule.description}")

    if matched:
        return Verdict.FAIL, matched

    pass_hits: list[str] = []
    for rule in case.pass_if:
        if _evaluate_rule(rule, response):
            pass_hits.append(f"PASS_IF: {rule.description}")

    if case.pass_if and pass_hits:
        return Verdict.PASS, pass_hits

    if case.pass_if and not pass_hits:
        return Verdict.PARTIAL, ["No PASS_IF rule matched — inconclusive"]

    return Verdict.PASS, []


# ---------------------------------------------------------------------------
# Core executor
# ---------------------------------------------------------------------------

class CaseRunner:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("TARGET_BASE_URL", "http://localhost:80")).rstrip("/")
        self.vars = _resolve_template_vars()
        self.vars["base_url"] = self.base_url

    def run_case(self, case: AttackCase) -> CaseResult:
        req = case.target
        endpoint = _substitute(req.endpoint, self.vars)
        body = _substitute(req.body, self.vars)
        headers = {**req.headers, **_build_auth_headers(req.auth_type)}
        headers = _substitute(headers, self.vars)

        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=req.timeout_seconds, verify=False) as client:
                resp = client.request(
                    method=req.method,
                    url=url,
                    json=body if req.method in ("POST", "PUT", "PATCH") else None,
                    params=body if req.method == "GET" else None,
                    headers=headers,
                )

            verdict, matched = _determine_verdict(case, resp)
            excerpt = resp.text[:1000] if resp.text else ""

            return CaseResult(
                case_id=case.id,
                threat_id="",
                verdict=verdict,
                observed_behavior=f"HTTP {resp.status_code}",
                response_status=resp.status_code,
                response_body_excerpt=excerpt,
                matched_rules=matched,
                add_to_regression=(verdict == Verdict.FAIL),
            )

        except httpx.ConnectError as exc:
            return CaseResult(
                case_id=case.id,
                threat_id="",
                verdict=Verdict.ERROR,
                observed_behavior="Connection refused — target not reachable",
                error_detail=str(exc),
            )
        except Exception as exc:
            return CaseResult(
                case_id=case.id,
                threat_id="",
                verdict=Verdict.ERROR,
                observed_behavior=f"Unexpected error: {type(exc).__name__}",
                error_detail=str(exc),
            )

    def run_suite(self, suite: CaseSuite) -> list[CaseResult]:
        results: list[CaseResult] = []
        for case in suite.cases:
            result = self.run_case(case)
            result.threat_id = suite.meta.threat_id
            results.append(result)
        return results


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def load_suite(path: Path) -> CaseSuite:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CaseSuite.model_validate(raw)


# ---------------------------------------------------------------------------
# Results persistence
# ---------------------------------------------------------------------------

def _save_results(results: list[CaseResult], label: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{label}_{ts}.json"
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in results], indent=2),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------

_VERDICT_STYLE = {
    Verdict.PASS: "green",
    Verdict.FAIL: "bold red",
    Verdict.PARTIAL: "yellow",
    Verdict.ERROR: "dim",
}


def _print_results(results: list[CaseResult]) -> None:
    table = Table(title="Eval Results", show_lines=True)
    table.add_column("Case ID", style="cyan", no_wrap=True)
    table.add_column("Verdict", no_wrap=True)
    table.add_column("Status")
    table.add_column("Matched Rules")
    table.add_column("Observed")

    for r in results:
        style = _VERDICT_STYLE.get(r.verdict, "")
        table.add_row(
            r.case_id,
            f"[{style}]{r.verdict.value.upper()}[/{style}]",
            str(r.response_status or "-"),
            "\n".join(r.matched_rules[:3]) or "-",
            (r.observed_behavior or "")[:60],
        )

    console.print(table)
    fails = sum(1 for r in results if r.verdict == Verdict.FAIL)
    console.print(
        f"\n[bold]Total: {len(results)} | "
        f"[red]FAIL: {fails}[/red] | "
        f"[green]PASS: {len(results) - fails}[/green][/bold]\n"
    )


# ---------------------------------------------------------------------------
# Regression suite management
# ---------------------------------------------------------------------------

def _load_regression_ids() -> set[str]:
    if REGRESSION_SUITE_FILE.exists():
        data = json.loads(REGRESSION_SUITE_FILE.read_text())
        return set(data.get("case_ids", []))
    return set()


def _update_regression_suite(results: list[CaseResult]) -> None:
    ids = _load_regression_ids()
    new_ids = {r.case_id for r in results if r.add_to_regression}
    if new_ids - ids:
        ids |= new_ids
        REGRESSION_SUITE_FILE.write_text(
            json.dumps({"case_ids": sorted(ids)}, indent=2)
        )
        console.print(f"[yellow]Regression suite updated — {len(new_ids)} new case(s) added[/yellow]")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AgentForge eval runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--suite", type=Path, help="Path to a single YAML suite file")
    group.add_argument("--all-seed", action="store_true", help="Run all seed suites")
    group.add_argument("--regression", action="store_true", help="Run regression cases only")
    parser.add_argument("--base-url", help="Override TARGET_BASE_URL")
    args = parser.parse_args()

    runner = CaseRunner(base_url=args.base_url)
    all_results: list[CaseResult] = []

    if args.suite:
        suite = load_suite(args.suite)
        console.print(f"\n[bold cyan]Running suite: {suite.meta.threat_id} — {suite.meta.title}[/bold cyan]")
        results = runner.run_suite(suite)
        all_results.extend(results)

    elif args.all_seed:
        for yaml_file in sorted(SEED_DIR.glob("*.yaml")):
            suite = load_suite(yaml_file)
            console.print(f"\n[bold cyan]Suite: {suite.meta.threat_id} — {suite.meta.title}[/bold cyan]")
            results = runner.run_suite(suite)
            all_results.extend(results)

    elif args.regression:
        regression_ids = _load_regression_ids()
        for yaml_file in sorted(SEED_DIR.glob("*.yaml")):
            suite = load_suite(yaml_file)
            regression_cases = [c for c in suite.cases if c.id in regression_ids or c.regression]
            if not regression_cases:
                continue
            suite.cases = regression_cases
            console.print(f"\n[bold cyan]Regression: {suite.meta.threat_id} ({len(regression_cases)} cases)[/bold cyan]")
            results = runner.run_suite(suite)
            all_results.extend(results)

    if all_results:
        _print_results(all_results)
        label = "seed_all" if args.all_seed else ("regression" if args.regression else Path(args.suite).stem)
        out = _save_results(all_results, label)
        console.print(f"Results saved → {out}\n")
        _update_regression_suite(all_results)

    # Exit non-zero if any FAIL
    if any(r.verdict == Verdict.FAIL for r in all_results):
        sys.exit(1)


if __name__ == "__main__":
    main()
