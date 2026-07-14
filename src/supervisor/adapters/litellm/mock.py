"""LiteLLM mock adapter — deterministic costs without API calls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockCompletionResult:
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class LiteLLMMockAdapter:
    """Returns deterministic token counts and costs for demo and tests."""

    DEFAULT_PRICING: dict[str, tuple[float, float]] = {
        "mock-research": (0.000001, 0.000002),
        "mock-synthesis": (0.000002, 0.000004),
        "mock-review": (0.000003, 0.000005),
    }

    def __init__(self, use_mock: bool = True) -> None:
        self.use_mock = use_mock

    def complete(
        self, model: str, prompt: str, max_output_tokens: int = 512
    ) -> MockCompletionResult:
        if not self.use_mock:
            raise RuntimeError(
                "Real LiteLLM calls are opt-in. Set USE_MOCK_MODELS=true or install litellm extra."
            )

        input_tokens = max(50, len(prompt) // 4)
        output_tokens = min(max_output_tokens, max(80, len(prompt) // 8))
        input_rate, output_rate = self.DEFAULT_PRICING.get(model, (0.000001, 0.000002))
        cost = (input_tokens * input_rate) + (output_tokens * output_rate)

        return MockCompletionResult(
            model=model,
            content=f"[mock response from {model}]",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
            latency_ms=120.0,
        )
