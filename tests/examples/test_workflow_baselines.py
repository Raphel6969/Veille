"""Stable Phase 0 regression baselines for the two demonstrable workflows."""

from __future__ import annotations

from examples.cited_market_research.agent import run_scenario as run_market_research
from examples.real_world_demo.agent import run_scenario as run_real_world


def test_market_research_success_baseline() -> None:
    result = run_market_research("success")

    assert result["validation"].task_contract_met is True
    assert result["total_cost_usd"] == 0.01384
    assert result["batch"].metadata["duplicate_search_count"] == 0
    assert result["batch"].metadata["retry_count"] == 0


def test_real_world_success_baseline() -> None:
    result = run_real_world("success")

    assert result["validation"]["task_contract_met"] is True
    assert result["total_cost_usd"] == 0.01
