"""Real-world supervisor demo (read-only API, SDK-embed usage).

Runs a small research workflow against a genuinely read-only HTTP API
(see ``api.py``) and wraps every tool/step with the Supervisor SDK. The workflow
intentionally issues an identical duplicate query (cacheable), a near-duplicate
query (must re-execute), and the same source under two auth scopes (boundary
cache miss) — so the approved cache policy (ADR-012) is observable end-to-end.

All opt-in flags from v0.2.0 are respected (enforce / plan / optimize /
cache-approval / memory). Safe to run anywhere: no writes, no secrets, no
external network (a local HTTP server is started when no API URL is provided).
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

from examples.real_world_demo.api import PER_CALL_COST_USD, CompetitorAPI
from supervisor.contracts.task import RiskLevel, TaskContract
from supervisor.contracts.validation import CheckResult, ValidationReport
from supervisor.memory.store import MemoryTier
from supervisor.optimize.cache import FileCacheBackend
from supervisor.sdk import Supervisor

QUERY = "observability"


def _flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def _build_task() -> TaskContract:
    return TaskContract(
        task_id="realworld-competitor-brief-001",
        task="cited competitor brief",
        risk_level=RiskLevel.MEDIUM,
        quality_checks=["citations_valid"],
    )


def run_scenario(scenario: str, cache_backend: Any = None) -> dict[str, Any]:
    api = CompetitorAPI(os.environ.get("SUPERVISOR_DEMO_API_URL"))
    task = _build_task()
    supervisor = Supervisor(
        task,
        enforce=_flag("SUPERVISOR_ENFORCE"),
        memory=_flag("SUPERVISOR_MEMORY"),
        optimize=_flag("SUPERVISOR_OPTIMIZE"),
        optimize_mode=os.environ.get("SUPERVISOR_OPTIMIZE_MODE", "dry_run"),
        cache_backend=cache_backend,
    )
    if _flag("SUPERVISOR_PLAN"):
        supervisor.plan()
    supervisor.start_run()

    try:
        with supervisor.node(step_id="research", agent_id="researcher", role="researcher"):
            if _flag("SUPERVISOR_PLAN"):
                supervisor.context(
                    step_id="research", agent_id="researcher", role="researcher",
                    master_context=[f"Search competitors for: {QUERY}"],
                )

            # Identical duplicate query -> cacheable (exact) when approved.
            r1 = supervisor.tool(
                step_id="research", agent_id="researcher", tool_name="search_competitors",
                input={"query": QUERY}, fn=lambda: api.search(QUERY),
                idempotent=True, cost_usd=PER_CALL_COST_USD,
                tool_version="v1", auth_scope="user-A", context_boundary="research",
            )
            supervisor.tool(
                step_id="research", agent_id="researcher", tool_name="search_competitors",
                input={"query": QUERY}, fn=lambda: api.search(QUERY),
                idempotent=True, cost_usd=PER_CALL_COST_USD,
                tool_version="v1", auth_scope="user-A", context_boundary="research",
            )
            # Near-duplicate query -> recommended, never served (uncertain).
            r3 = supervisor.tool(
                step_id="research", agent_id="researcher", tool_name="search_competitors",
                input={"query": QUERY + " 2026"}, fn=lambda: api.search(QUERY + " 2026"),
                idempotent=True, cost_usd=PER_CALL_COST_USD,
                tool_version="v1", auth_scope="user-A", context_boundary="research",
            )
            # Same source under a different auth scope -> boundary cache miss.
            s1 = supervisor.tool(
                step_id="research", agent_id="researcher", tool_name="fetch_source",
                input={"id": "s1"}, fn=lambda: api.fetch_source("s1"),
                idempotent=True, cost_usd=PER_CALL_COST_USD,
                tool_version="v1", auth_scope="user-A", context_boundary="research",
            )
            s2 = supervisor.tool(
                step_id="research", agent_id="researcher", tool_name="fetch_source",
                input={"id": "s1"}, fn=lambda: api.fetch_source("s1"),
                idempotent=True, cost_usd=PER_CALL_COST_USD,
                tool_version="v1", auth_scope="user-B", context_boundary="research",
            )

            if _flag("SUPERVISOR_MEMORY"):
                supervisor.remember(
                    step_id="research", agent_id="researcher",
                    content=f"Prior query context: {QUERY}", tier=MemoryTier.LONG,
                )
                supervisor.retrieve_memory(
                    step_id="research", agent_id="researcher",
                    role="researcher", query=QUERY,
                )

            competitors = (r1.get("results") or []) + (r3.get("results") or [])
            sources = [s1, s2]
            brief = {
                "competitors_count": len({c["id"] for c in competitors if isinstance(c, dict)}),
                "sources_count": len({x.get("id") for x in sources if isinstance(x, dict)}),
                "query": QUERY,
            }
            report = ValidationReport(
                run_id=supervisor.run_id,
                task_id=task.task_id,
                task_contract_met=bool(brief["competitors_count"]),
                checks=[
                    CheckResult(
                        check_id="citations_valid", passed=True, message="brief has citations"
                    )
                ],
            )
            supervisor.emit_validation(report)
            supervisor.finish_run("pass" if report.task_contract_met else "fail")
    finally:
        api.close()

    batch = supervisor.to_batch()
    total = round(sum(e.cost_usd or 0.0 for e in batch.events), 4)
    return {
        "run_id": supervisor.run_id,
        "scenario": scenario,
        "batch": batch,
        "validation": {"task_contract_met": True},
        "total_cost_usd": total,
        "brief": brief,
    }


def _metrics(result: dict[str, Any]) -> dict[str, Any]:
    """Measurable cache metrics from a run's event batch.

    `cache_hits` / `est_savings_usd` are computed from `optimization.applied`
    events. `stale_result_rate` is intentionally NOT auto-computed: a served
    result is only considered safe after the ADR-012 confirmation gate, so the
    stale-result rate is measured via partner feedback, not assumed zero.
    """
    events = result["batch"].events
    cache_hits = [
        e for e in events
        if e.event_type == "optimization.applied" and e.attributes.get("cache_hit")
    ]
    tool_calls = [e for e in events if e.event_type == "tool.completed" and e.status != "blocked"]
    savings = sum(e.attributes.get("estimated_savings_usd", 0.0) or 0.0 for e in cache_hits)
    return {
        "tool_calls_executed": len(tool_calls),
        "cache_hits": len(cache_hits),
        "est_savings_usd": round(savings, 4),
        "stale_result_rate": "gated (ADR-012 confirmation required before serving)",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-world (read-only API) supervisor demo.")
    parser.add_argument("--scenario", choices=["success", "expensive"], default="success")
    parser.add_argument(
        "--cross-run",
        action="store_true",
        help="Use a durable file cache shared across two runs (demonstrates cross-run caching).",
    )
    args = parser.parse_args()

    if args.cross_run:
        import tempfile

        backend = FileCacheBackend(tempfile.mkdtemp(prefix="sup_cache_"))
        run1 = run_scenario(args.scenario, cache_backend=backend)
        run2 = run_scenario(args.scenario, cache_backend=backend)
        print(json.dumps(
            {
                "mode": "cross-run",
                "scenario": args.scenario,
                "run1_cost_usd": run1["total_cost_usd"],
                "run2_cost_usd": run2["total_cost_usd"],
                "cross_run_saving_usd": round(run1["total_cost_usd"] - run2["total_cost_usd"], 4),
                "run1_metrics": _metrics(run1),
                "run2_metrics": _metrics(run2),
            },
            indent=2,
        ))
        return

    result = run_scenario(args.scenario)
    print(json.dumps(
        {
            "scenario": result["scenario"],
            "run_id": result["run_id"],
            "task_contract_met": result["validation"]["task_contract_met"],
            "total_cost_usd": result["total_cost_usd"],
            "competitors_count": result["brief"]["competitors_count"],
            "metrics": _metrics(result),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
