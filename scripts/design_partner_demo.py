"""Design-partner demo harness for the AI Runtime Supervisor (v0.2.0).

Runs the cited-market-research workflow under representative opt-in configurations
and produces a per-run "observation packet" mapped to the five questions we need
design-partner feedback on:

  1. Are cost tiers understandable and trusted?
  2. Do intervention explanations feel safe?
  3. Which repeated tool calls are actually cacheable?
  4. What cache freshness / expiry rules are acceptable?
  5. Is adaptive rerouting welcome, or should it stay advisory?

The harness captures OBJECTIVE system signals only. Partner responses are captured
separately (see docs/design-partner-feedback/capture-template.md). Run `--matrix`
to generate the system-evidence baseline across scenarios + flag presets.

Usage:
    # one demo for a partner (they answer the printed questions)
    python -m scripts.design_partner_demo --scenario expensive --partner P1

    # generate the system-signal baseline across the demo matrix
    python -m scripts.design_partner_demo --matrix
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from examples.cited_market_research.agent import run_scenario

from supervisor.analytics.run_summary import RunSummary, summarize
from supervisor.contracts.events import EventType

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_DIR = ROOT / "docs" / "design-partner-feedback"
RUNS_DIR = FEEDBACK_DIR / "runs"

CACHE_DEFAULT_TTL = 300.0  # seconds, InMemoryCache default
MEMORY_DEFAULT_TTL = None  # MemoryRecord.ttl_seconds default (no expiry)

FLAG_PRESETS: dict[str, dict[str, str]] = {
    "baseline": {},
    "plan": {"SUPERVISOR_PLAN": "1"},
    "optimize_active": {
        "SUPERVISOR_OPTIMIZE": "1",
        "SUPERVISOR_OPTIMIZE_MODE": "active",
        "SUPERVISOR_CACHE_APPROVED": "1",
    },
    "memory": {"SUPERVISOR_MEMORY": "1"},
    "all": {
        "SUPERVISOR_PLAN": "1",
        "SUPERVISOR_OPTIMIZE": "1",
        "SUPERVISOR_OPTIMIZE_MODE": "active",
        "SUPERVISOR_CACHE_APPROVED": "1",
        "SUPERVISOR_MEMORY": "1",
    },
}

QUESTIONS: list[dict[str, str]] = [
    {
        "id": "cost_tiers",
        "question": "Are the cost tiers understandable and trusted?",
        "evidence_key": "cost_tiers",
    },
    {
        "id": "intervention_safety",
        "question": "Do the intervention explanations feel safe?",
        "evidence_key": "interventions",
    },
    {
        "id": "cacheable_calls",
        "question": "Which repeated tool calls are actually cacheable?",
        "evidence_key": "cacheable_calls",
    },
    {
        "id": "cache_freshness",
        "question": "What cache freshness / expiry rules are acceptable?",
        "evidence_key": "freshness",
    },
    {
        "id": "rerouting",
        "question": "Is adaptive rerouting welcome, or should it stay advisory?",
        "evidence_key": "rerouting",
    },
]


def _attrs(e: Any) -> dict[str, Any]:
    return getattr(e, "attributes", {}) or {}


def _field(e: Any, name: str, default: Any = None) -> Any:
    val = getattr(e, name, None)
    if val is not None:
        return val
    return _attrs(e).get(name, default)


def _run_with_flags(scenario: str, flags: dict[str, str]) -> tuple[Any, list[Any], RunSummary]:
    env_keys = [
        "SUPERVISOR_ENFORCE",
        "SUPERVISOR_PLAN",
        "SUPERVISOR_OPTIMIZE",
        "SUPERVISOR_OPTIMIZE_MODE",
        "SUPERVISOR_MEMORY",
    ]
    prev = {k: os.environ.get(k) for k in env_keys}
    for k in env_keys:
        os.environ.pop(k, None)
    for k, v in flags.items():
        os.environ[k] = v
    try:
        _scn = cast("Literal['success', 'expensive', 'failed_validation']", scenario)
        result = run_scenario(_scn)
    finally:
        for k in env_keys:
            os.environ.pop(k, None)
        for k in env_keys:
            val = prev.get(k)
            if val is not None:
                os.environ[k] = val
            else:
                os.environ.pop(k, None)
    batch = result["batch"]
    events = list(batch.events)
    summary = summarize(batch)
    return result, events, summary


def _cost_tiers(events: list[Any], summary: RunSummary, flags: dict[str, str]) -> dict[str, Any]:
    run_started = next((e for e in events if e.event_type == EventType.RUN_STARTED), None)
    plan_enabled = bool(flags.get("SUPERVISOR_PLAN"))
    model_costs: list[dict[str, Any]] = []
    for e in events:
        if e.event_type == EventType.MODEL_REQUESTED:
            a = _attrs(e)
            model_costs.append(
                {
                    "step": _field(e, "step_id"),
                    "agent": _field(e, "agent_id"),
                    "model": _field(e, "model"),
                    "cost_usd": round(e.cost_usd or 0.0, 4),
                    "routing_tier": a.get("routing_tier"),
                }
            )
    return {
        "plan_enabled": plan_enabled,
        "plan_tier": summary.plan_tier,
        "tier_on_run_started": _attrs(run_started).get("tier") if run_started else None,
        "total_cost_usd": round(sum(e.cost_usd or 0.0 for e in events), 4),
        "per_model_cost": model_costs,
        "note": (
            "Tier is advisory and only emitted when SUPERVISOR_PLAN=1. "
            "Tier estimate multipliers live in the planner, not the event stream."
        ),
    }


def _interventions(events: list[Any]) -> dict[str, Any]:
    applied = []
    for e in events:
        if e.event_type == EventType.INTERVENTION_APPLIED:
            a = _attrs(e)
            applied.append(
                {
                    "action": a.get("action"),
                    "policy_id": a.get("policy_id"),
                    "reason": a.get("reason"),
                    "human_review_required": a.get("human_review_required"),
                }
            )
    triggered = []
    for e in events:
        if e.event_type == EventType.POLICY_TRIGGERED:
            a = _attrs(e)
            triggered.append(
                {
                    "policy_id": a.get("policy_id"),
                    "reason": a.get("reason"),
                    "severity": a.get("severity"),
                }
            )
    return {
        "interventions_applied": applied,
        "policies_triggered_observe": triggered,
        "count_applied": len(applied),
        "count_triggered": len(triggered),
        "note": (
            "With enforcement off (default), interventions are observe-only "
            "policy.triggered events; SUPERVISOR_ENFORCE=true emits intervention.applied."
        ),
    }


def _cacheable_calls(events: list[Any], summary: RunSummary) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    opt_by_tool: dict[str, list[str]] = defaultdict(list)
    for e in events:
        if e.event_type in (EventType.OPTIMIZATION_RECOMMENDED, EventType.OPTIMIZATION_APPLIED):
            a = _attrs(e)
            tn = getattr(e, "tool_name", None)
            if tn:
                opt_by_tool[tn].append(a.get("match_type") or "unknown")
    for e in events:
        if e.event_type == EventType.TOOL_REQUESTED:
            # Count only SDK-originated tool events (the adapter also emits
            # tool.requested callbacks without a stable tool_name).
            tool = getattr(e, "tool_name", None)
            if not tool:
                continue
            a = _attrs(e)
            inp = a.get("input")
            key = f"{tool}::{json.dumps(inp, sort_keys=True, default=str)}"
            g = groups.setdefault(
                key,
                {"tool": tool, "input": inp, "count": 0,
                 "idempotent": a.get("idempotent"),
                 "match_types": list(opt_by_tool.get(tool, []))},
            )
            g["count"] += 1
    repeated = [g for g in groups.values() if g["count"] > 1]
    cacheable = [
        g
        for g in repeated
        if g.get("idempotent") is True or any(m in ("exact", "semantic") for m in g["match_types"])
    ]
    return {
        "distinct_tool_inputs": len(groups),
        "repeated_groups": repeated,
        "cacheable_candidates": cacheable,
        "summary_semantic_duplicates": summary.semantic_duplicates,
        "summary_cache_hits": summary.cache_hits,
        "summary_cache_served": summary.cache_served,
        "summary_estimated_savings_usd": summary.estimated_savings_usd,
    }


def _freshness(events: list[Any], flags: dict[str, str]) -> dict[str, Any]:
    memory_retrieved = []
    for e in events:
        if e.event_type == EventType.MEMORY_RETRIEVED:
            a = _attrs(e)
            memory_retrieved.append(
                {
                    "role": a.get("role"),
                    "included": a.get("included"),
                    "excluded": a.get("excluded"),
                    "stale": a.get("stale"),
                    "drift": a.get("drift"),
                    "reason": a.get("reason"),
                }
            )
    return {
        "cache_default_ttl_seconds": CACHE_DEFAULT_TTL,
        "memory_default_ttl_seconds": MEMORY_DEFAULT_TTL,
        "memory_enabled": bool(flags.get("SUPERVISOR_MEMORY")),
        "memory_retrieved": memory_retrieved,
        "proposed_cache_rule": "Serve idempotent hits up to cache TTL (default 300s); "
        "do not serve across runs unless a durable backend is enabled.",
        "proposed_memory_rule": "working/short tiers expire ~session; long tier persists "
        "with optional TTL; drift (content hash change) excludes from retrieval, never "
        "auto-deletes.",
    }


def _rerouting(events: list[Any], flags: dict[str, str]) -> dict[str, Any]:
    routed: list[dict[str, Any]] = []
    for e in events:
        if e.event_type == EventType.MODEL_REQUESTED:
            a = _attrs(e)
            if a.get("routing_tier") or a.get("routing_capability"):
                routed.append(
                    {
                        "step": _field(e, "step_id"),
                        "agent": _field(e, "agent_id"),
                        "model": _field(e, "model"),
                        "routing_tier": a.get("routing_tier"),
                        "routing_capability": a.get("routing_capability"),
                        "routing_reason": a.get("routing_reason"),
                    }
                )
    return {
        "plan_enabled": bool(flags.get("SUPERVISOR_PLAN")),
        "routed_calls": routed,
        "note": "Routing is advisory today: it annotates model.requested with routing_tier; "
        "it never rewrites or blocks execution. Enforcement would be a separate opt-in.",
    }


def build_packet(scenario: str, flags: dict[str, str], label: str) -> dict[str, Any]:
    result, events, summary = _run_with_flags(scenario, flags)
    packet: dict[str, Any] = {
        "schema": "design-partner-packet/1",
        "generated_at": datetime.now(UTC).isoformat(),
        "supervisor_version": "0.2.0",
        "scenario": scenario,
        "flag_preset": label,
        "flags": flags,
        "task_contract_met": result["validation"].task_contract_met,
        "total_cost_usd": round(result["total_cost_usd"], 4),
        "cost_tiers": _cost_tiers(events, summary, flags),
        "interventions": _interventions(events),
        "cacheable_calls": _cacheable_calls(events, summary),
        "freshness": _freshness(events, flags),
        "rerouting": _rerouting(events, flags),
        "partner_responses": {q["id"]: None for q in QUESTIONS},
    }
    return packet


def print_packet(packet: dict[str, Any]) -> None:
    print("=" * 72)
    print(f"SCENARIO: {packet['scenario']}  PRESET: {packet['flag_preset']}  "
          f"COST: ${packet['total_cost_usd']}  MET: {packet['task_contract_met']}")
    print("=" * 72)
    for q in QUESTIONS:
        ev = packet[q["evidence_key"]]
        print(f"\n### {q['id']}: {q['question']}")
        print(json.dumps(ev, indent=2, default=str))
        print(f"  >>> partner response: {packet['partner_responses'][q['id']]}")


def _write_run(packet: dict[str, Any], partner: str) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{partner}__{packet['scenario']}__{packet['flag_preset']}.json"
    out = RUNS_DIR / fname
    out.write_text(json.dumps(packet, indent=2, default=str))
    return out


def _matrix() -> None:
    scenarios = ["success", "expensive", "failed_validation"]
    # A representative 6-demo matrix (within the 5-10 target).
    matrix = [
        ("expensive", "all"),
        ("expensive", "optimize_active"),
        ("expensive", "plan"),
        ("success", "all"),
        ("failed_validation", "all"),
        ("expensive", "memory"),
    ]
    packets = []
    for scenario, preset in matrix:
        if scenario not in scenarios:
            continue
        flags = FLAG_PRESETS[preset]
        packet = build_packet(scenario, flags, preset)
        packets.append(packet)
        print_packet(packet)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "matrix-analysis.json").write_text(json.dumps(packets, indent=2, default=str))
    _write_system_signals(packets)
    print(f"\nWrote {len(packets)} packets to {RUNS_DIR}")


def _write_system_signals(packets: list[dict[str, Any]]) -> None:
    lines = ["# v0.2.0 design-partner system signals (objective, pre-human)", "",
             "Generated by `python -m scripts.design_partner_demo --matrix`.",
             "These are OBJECTIVE signals the supervisor emits today. Partner",
             "responses are captured separately via capture-template.md.",
             "", "## Q3 — Repeated / cacheable tool calls"]
    for p in packets:
        c = p["cacheable_calls"]
        if c["repeated_groups"]:
            lines.append(f"\n### {p['scenario']} / {p['flag_preset']}")
            for g in c["repeated_groups"]:
                tag = "CACHEABLE" if g in c["cacheable_candidates"] else "repeat (not cacheable)"
                lines.append(f"- `{g['tool']}` x{g['count']} — {tag} "
                             f"(idempotent={g.get('idempotent')}, matches={g['match_types']})")
            lines.append(f"  summary: semantic_duplicates={c['summary_semantic_duplicates']}, "
                         f"cache_served={c['summary_cache_served']}, "
                         f"savings=${c['summary_estimated_savings_usd']}")
    lines.append("\n## Q1 — Cost tiers (when plan enabled)")
    for p in packets:
        t = p["cost_tiers"]
        if t["plan_enabled"]:
            lines.append(f"- {p['scenario']}/{p['flag_preset']}: plan_tier={t['plan_tier']}, "
                         f"total=${t['total_cost_usd']}")
    lines.append("\n## Q5 — Routing (advisory, when plan enabled)")
    for p in packets:
        r = p["rerouting"]
        if r["plan_enabled"] and r["routed_calls"]:
            for rc in r["routed_calls"]:
                lines.append(f"- {p['scenario']}/{rc['step']}/{rc['agent']}: "
                             f"model={rc['model']} tier={rc['routing_tier']} "
                             f"reason={rc['routing_reason']}")
    lines.append("\n## Q4 — Freshness defaults observed")
    lines.append(f"- cache default TTL = {CACHE_DEFAULT_TTL}s; "
                 f"memory default TTL = {MEMORY_DEFAULT_TTL}")
    lines.append("\n## Q2 — Intervention explanations")
    for p in packets:
        iv = p["interventions"]
        if iv["count_applied"] or iv["count_triggered"]:
            lines.append(f"- {p['scenario']}/{p['flag_preset']}: "
                         f"applied={iv['count_applied']}, triggered={iv['count_triggered']}")
    (FEEDBACK_DIR / "system-signals.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Design-partner demo harness (v0.2.0).")
    parser.add_argument("--scenario", choices=["success", "expensive", "failed_validation", "all"],
                        default="expensive")
    parser.add_argument("--preset", choices=list(FLAG_PRESETS), default="all")
    parser.add_argument("--partner", default="PARTNER")
    parser.add_argument("--matrix", action="store_true", help="Run the 6-demo baseline matrix.")
    args = parser.parse_args()

    if args.matrix:
        _matrix()
        return

    scenarios = (
        ["success", "expensive", "failed_validation"] if args.scenario == "all" else [args.scenario]
    )
    for scenario in scenarios:
        flags = FLAG_PRESETS[args.preset]
        packet = build_packet(scenario, flags, args.preset)
        print_packet(packet)
        out = _write_run(packet, args.partner)
        print(f"\n[wrote packet: {out}]")


if __name__ == "__main__":
    main()
