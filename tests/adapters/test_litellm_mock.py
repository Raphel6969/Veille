import pytest

from supervisor.adapters.litellm.mock import LiteLLMMockAdapter


def test_mock_completion_deterministic() -> None:
    adapter = LiteLLMMockAdapter(use_mock=True)
    result = adapter.complete("mock-research", "Analyze competitors in AI supervision.")
    assert result.model == "mock-research"
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.cost_usd > 0
    assert "[mock response" in result.content


def test_real_calls_require_opt_in() -> None:
    adapter = LiteLLMMockAdapter(use_mock=False)
    with pytest.raises(RuntimeError, match="opt-in"):
        adapter.complete("gpt-4o-mini", "test")
