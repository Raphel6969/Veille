"""Tests for the real-world (read-only API) supervisor demo.

Verifies the demo runs fully offline (local read-only HTTP server), and that the
approved cache policy serves the identical duplicate query while the gate blocks
serving until confirmation.
"""

from __future__ import annotations

import os

from examples.real_world_demo.agent import run_scenario

from supervisor.contracts.events import EventType


def _count(events, et: EventType) -> int:
    return sum(1 for e in events if e.event_type == et)


def test_runs_offline_and_met() -> None:
    result = run_scenario("success")
    assert result["validation"]["task_contract_met"] is True
    assert result["brief"]["competitors_count"] == 2
    # 5 tool calls executed (no caching by default).
    assert result["total_cost_usd"] == 0.01


def test_cache_serves_identical_duplicate_when_approved() -> None:
    os.environ["SUPERVISOR_OPTIMIZE"] = "1"
    os.environ["SUPERVISOR_OPTIMIZE_MODE"] = "active"
    os.environ["SUPERVISOR_CACHE_APPROVED"] = "1"
    try:
        result = run_scenario("success")
    finally:
        os.environ.pop("SUPERVISOR_OPTIMIZE", None)
        os.environ.pop("SUPERVISOR_OPTIMIZE_MODE", None)
        os.environ.pop("SUPERVISOR_CACHE_APPROVED", None)

    # Duplicate identical search served -> 4 executed calls (saved 0.002).
    assert result["total_cost_usd"] == 0.008
    applied = [e for e in result["batch"].events if e.event_type == EventType.OPTIMIZATION_APPLIED]
    assert applied, "expected an optimization.applied for the identical duplicate"
    assert applied[0].attributes.get("match_type") == "exact"
    assert applied[0].tool_name == "search_competitors"


def test_gate_blocks_serving_without_confirmation() -> None:
    os.environ["SUPERVISOR_OPTIMIZE"] = "1"
    os.environ["SUPERVISOR_OPTIMIZE_MODE"] = "active"
    # No SUPERVISOR_CACHE_APPROVED / confirmations -> gate not met.
    try:
        result = run_scenario("success")
    finally:
        os.environ.pop("SUPERVISOR_OPTIMIZE", None)
        os.environ.pop("SUPERVISOR_OPTIMIZE_MODE", None)

    # Gate not met -> nothing served -> all 5 calls execute.
    assert result["total_cost_usd"] == 0.01
    applied = [e for e in result["batch"].events if e.event_type == EventType.OPTIMIZATION_APPLIED]
    assert not applied
