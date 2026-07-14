"""RunExplorer — rich, multi-view projection over a RunEventBatch.

Extends (does not replace) ``analytics.summarize``. Produces the views the Local
Integration Console needs: timeline, execution/agent graphs, planner decisions,
policy/intervention/validation rollups, cache reuse reasons, context
compression/diversification, and estimated-vs-actual cost when a task contract is
available.
"""

from __future__ import annotations

from typing import Any

from supervisor.analytics import summarize
from supervisor.context.diversification import (
    compression_reports,
    diversification_reports,
)
from supervisor.contracts.events import EventType, RunEventBatch
from supervisor.planning import Planner, estimate


def _timeline(batch: RunEventBatch) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "step_id": e.step_id,
            "agent_id": e.agent_id,
            "tool_name": e.tool_name,
            "model_name": e.model_name,
            "duration_ms": e.duration_ms,
            "cost_usd": e.cost_usd,
            "status": e.status,
            "attributes": e.attributes,
        }
        for e in batch.events
    ]


def _execution_graph(batch: RunEventBatch) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    last_step: str | None = None
    for e in batch.events:
        if e.step_id:
            if e.step_id not in nodes:
                nodes[e.step_id] = {
                    "step_id": e.step_id,
                    "agent_id": e.agent_id,
                    "events": 0,
                }
            nodes[e.step_id]["events"] += 1
            if last_step is not None and last_step != e.step_id:
                edges.append({"from": last_step, "to": e.step_id})
            last_step = e.step_id
    return {"nodes": list(nodes.values()), "edges": edges}


def _agent_graph(batch: RunEventBatch) -> dict[str, Any]:
    agents: dict[str, dict[str, Any]] = {}
    for e in batch.events:
        if e.agent_id:
            a = agents.setdefault(
                e.agent_id, {"agent_id": e.agent_id, "steps": [], "events": 0}
            )
            a["events"] += 1
            if e.step_id and e.step_id not in a["steps"]:
                a["steps"].append(e.step_id)
    return {"nodes": list(agents.values())}


def _policy_intervention(batch: RunEventBatch) -> dict[str, Any]:
    policy = [
        {
            "event_type": e.event_type,
            "step_id": e.step_id,
            "tool_name": e.tool_name,
            "attributes": e.attributes,
        }
        for e in batch.events
        if e.event_type == EventType.POLICY_TRIGGERED
    ]
    interventions = [
        {
            "step_id": e.step_id,
            "tool_name": e.tool_name,
            "attributes": e.attributes,
        }
        for e in batch.events
        if e.event_type == EventType.INTERVENTION_APPLIED
    ]
    return {"policy_events": policy, "intervention_events": interventions}


def _validation(batch: RunEventBatch) -> dict[str, Any] | None:
    ev = next((e for e in batch.events if e.event_type == EventType.VALIDATION_COMPLETED), None)
    if ev is None:
        return None
    return {
        "status": ev.status,
        "checks": ev.attributes.get("checks") or [],
    }


def _cache_view(batch: RunEventBatch) -> dict[str, Any]:
    summary = summarize(batch)
    requested = sum(
        1
        for e in batch.events
        if e.event_type in (EventType.TOOL_REQUESTED, EventType.MODEL_REQUESTED)
        and e.attributes.get("match_type")
    )
    served = summary.cache_served
    return {
        "hits": summary.cache_hits,
        "served": served,
        "misses": max(0, requested - served),
        "reuse_reasons": [c.get("reuse_reason") for c in summary.cache_reuse],
        "reuse_detail": summary.cache_reuse,
    }


def _context_view(batch: RunEventBatch) -> dict[str, Any]:
    comp = [c.model_dump() for c in compression_reports(batch)]
    div = [d.model_dump() for d in diversification_reports(batch)]
    return {
        "compression": comp,
        "diversification": div,
        "redundant_slices": sum(1 for d in div if d["redundant"]),
    }


def _planner_view(batch: RunEventBatch, task: Any = None) -> dict[str, Any]:
    started = next((e for e in batch.events if e.event_type == EventType.RUN_STARTED), None)
    selected_tier = started.attributes.get("tier") if started is not None else None
    out: dict[str, Any] = {"selected_tier": selected_tier, "tier_options": None, "steps": None}
    if task is not None:
        try:
            plan = Planner().build_plan(task)
            out["tier_options"] = [t.model_dump() for t in plan.tier_options]
            out["steps"] = [s.model_dump() for s in plan.steps]
        except Exception:  # noqa: BLE001
            pass
    return out


def _estimated_vs_actual(batch: RunEventBatch, task: Any = None) -> dict[str, Any] | None:
    summary = summarize(batch)
    actual = {
        "cost_usd": summary.total_cost_usd,
        "latency_s": summary.total_latency_s,
        "tokens_in": summary.total_tokens_in,
        "tokens_out": summary.total_tokens_out,
    }
    if task is None:
        return {"actual": actual, "estimated": None}
    try:
        started = next(
            (e for e in batch.events if e.event_type == EventType.RUN_STARTED), None
        )
        tier = started.attributes.get("tier") if started is not None else None
        from supervisor.contracts.plan import PlanTier

        if tier is None:
            return {"actual": actual, "estimated": None}
        est = estimate(PlanTier(tier), task)
        estimated = {
            "cost_usd_min": est.estimated_cost_usd_min,
            "cost_usd_max": est.estimated_cost_usd_max,
            "latency_s_min": est.estimated_latency_seconds_min,
            "latency_s_max": est.estimated_latency_seconds_max,
            "tokens_min": est.estimated_tokens_min,
            "tokens_max": est.estimated_tokens_max,
        }
        return {"actual": actual, "estimated": estimated}
    except Exception:  # noqa: BLE001
        return {"actual": actual, "estimated": None}


def explore(batch: RunEventBatch, *, task: Any = None) -> dict[str, Any]:
    summary = summarize(batch)
    return {
        "run_id": batch.run_id,
        "task_id": batch.task_id,
        "summary": _summary_dict(summary),
        "timeline": _timeline(batch),
        "execution_graph": _execution_graph(batch),
        "agent_graph": _agent_graph(batch),
        "planner": _planner_view(batch, task),
        "estimated_vs_actual": _estimated_vs_actual(batch, task),
        "policy": _policy_intervention(batch),
        "validation": _validation(batch),
        "cache": _cache_view(batch),
        "context": _context_view(batch),
        "routing": summary.routing,
        "providers": summary.providers,
    }


def _summary_dict(summary: Any) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(summary)


def explore_run(
    run_id: str, *, task: Any = None, traces_dir: str = "fixtures/traces"
) -> dict[str, Any]:
    from supervisor.console.run_registry import load_run

    batch = load_run(run_id, traces_dir)
    return explore(batch, task=task)
