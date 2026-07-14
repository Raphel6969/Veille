"""Tests for the real OpenAI integration agent.

Real-provider tests are gated by the presence of ``OPENAI_API_KEY`` so they
pass in CI (no key) and run locally when credentials are configured.
"""

from __future__ import annotations

import os

import pytest
from examples.real_openai_agent.agent import run_scenario

REAL_MARK = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping real-provider test",
)


class TestRealOpenAIAgentMock:
    """Mock mode tests — always run, no credentials needed."""

    def test_mock_scenario_completes(self) -> None:
        result = run_scenario("success", use_mock=True)
        assert result["mode"] == "mock"
        assert result["run_id"]
        assert result["model_response"]
        assert result["total_cost_usd"] >= 0
        assert result["competitors_queried"] == 3

    def test_mock_emits_run_events(self) -> None:
        result = run_scenario("success", use_mock=True)
        assert len(result["batch"].events) >= 10
        assert result["batch"].run_id == result["run_id"]


class TestRealOpenAIAgentReal:
    """Real mode tests — require OPENAI_API_KEY."""

    @REAL_MARK
    def test_real_scenario_completes(self) -> None:
        result = run_scenario("success", use_mock=False)
        assert result["mode"] == "real"
        assert result["run_id"]
        assert result["model_response"]
        assert result["total_cost_usd"] >= 0
        assert result["competitors_queried"] == 3
