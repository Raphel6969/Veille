"""Provider abstraction for model completion.

Every provider implements :class:`ModelProvider` and supports a mock mode (no
network, deterministic) plus an opt-in real mode that routes through ``litellm``.
Provider credentials are read from the environment on demand and never stored on
serializable structures.
"""

from __future__ import annotations

import os
import time
from typing import Protocol

from supervisor._provider_util import (
    _derive_provider,  # noqa: F401  re-exported for backward compat
)
from supervisor.adapters.litellm.mock import LiteLLMMockAdapter, MockCompletionResult


class ModelProvider(Protocol):
    """Port implemented by every model provider (LiteLLM/OpenRouter/OpenAI/...)."""

    name: str

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        max_output_tokens: int = 512,
        use_mock: bool | None = None,
    ) -> MockCompletionResult: ...

    def is_configured(self, use_mock: bool | None = None) -> bool:
        """True when the provider can serve (mock always; real needs a credential)."""
        ...


class BaseModelProvider:
    """Shared mock + real (litellm) completion logic for all providers."""

    name: str = "base"
    api_base: str | None = None
    api_key_env: str | None = None
    mock_models: tuple[str, ...] = (
        "mock-research",
        "mock-analysis",
        "mock-synthesis",
        "mock-review",
    )

    def __init__(self, use_mock: bool = True) -> None:
        self.use_mock = use_mock

    def _real(self, model: str, prompt: str, max_output_tokens: int) -> MockCompletionResult:
        try:
            import litellm  # lazy: optional dependency
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "litellm is required for real provider calls. Install the 'litellm' extra."
            ) from exc
        api_key = os.getenv(self.api_key_env) if self.api_key_env else None
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_output_tokens,
            api_base=self.api_base,
            api_key=api_key,
        )
        usage = resp.usage or {}
        in_t = int(getattr(usage, "prompt_tokens", 0) or 0)
        out_t = int(getattr(usage, "completion_tokens", 0) or 0)
        cost = (in_t * 0.000001) + (out_t * 0.000002)
        return MockCompletionResult(
            model=model,
            content=str(getattr(resp.choices[0].message, "content", "")),
            input_tokens=in_t,
            output_tokens=out_t,
            cost_usd=round(cost, 6),
            latency_ms=round((time.monotonic() % 1) * 1000, 1),
        )

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        max_output_tokens: int = 512,
        use_mock: bool | None = None,
    ) -> MockCompletionResult:
        mock = self.use_mock if use_mock is None else use_mock
        if mock or model.startswith("mock"):
            return LiteLLMMockAdapter(use_mock=True).complete(model, prompt, max_output_tokens)
        return self._real(model, prompt, max_output_tokens)

    def is_configured(self, use_mock: bool | None = None) -> bool:
        mock = self.use_mock if use_mock is None else use_mock
        if mock:
            return True
        if not self.api_key_env:
            return True  # e.g. Ollama/LM Studio are local
        return bool(os.getenv(self.api_key_env))


class LiteLLMProvider(BaseModelProvider):
    name = "litellm"
    api_key_env = "OPENAI_API_KEY"


class OpenAICompatibleProvider(BaseModelProvider):
    """OpenAI-compatible endpoint (OpenAI, or any /v1 compatible server)."""

    name = "openai-compatible"
    api_key_env = "OPENAI_API_KEY"

    def __init__(
        self,
        use_mock: bool = True,
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        name: str = "openai-compatible",
    ) -> None:
        super().__init__(use_mock=use_mock)
        self.api_base = api_base
        self.api_key_env = api_key_env or self.api_key_env
        self.name = name


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    api_base = "https://openrouter.ai/api/v1"
    api_key_env = "OPENROUTER_API_KEY"

    def __init__(self, use_mock: bool = True) -> None:
        super().__init__(
            use_mock=use_mock,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
            name="openrouter",
        )


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    api_key_env = "OPENAI_API_KEY"

    def __init__(self, use_mock: bool = True) -> None:
        super().__init__(
            use_mock=use_mock, api_base=None, api_key_env=self.api_key_env, name="openai"
        )


class AnthropicProvider(OpenAICompatibleProvider):
    name = "anthropic"
    api_base = "https://api.anthropic.com/v1"
    api_key_env = "ANTHROPIC_API_KEY"

    def __init__(self, use_mock: bool = True) -> None:
        super().__init__(
            use_mock=use_mock,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
            name="anthropic",
        )


class GeminiProvider(OpenAICompatibleProvider):
    name = "gemini"
    api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
    api_key_env = "GEMINI_API_KEY"

    def __init__(self, use_mock: bool = True) -> None:
        super().__init__(
            use_mock=use_mock,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
            name="gemini",
        )


class OllamaProvider(OpenAICompatibleProvider):
    name = "ollama"
    api_base = "http://localhost:11434/v1"
    api_key_env = "OLLAMA_BASE_URL"

    def __init__(self, use_mock: bool = True) -> None:
        super().__init__(
            use_mock=use_mock,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
            name="ollama",
        )


class LMStudioProvider(OpenAICompatibleProvider):
    name = "lmstudio"
    api_base = "http://localhost:1234/v1"
    api_key_env = "LMSTUDIO_BASE_URL"

    def __init__(self, use_mock: bool = True) -> None:
        super().__init__(
            use_mock=use_mock,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
            name="lmstudio",
        )


_PROVIDERS: dict[str, type[BaseModelProvider]] = {
    "litellm": LiteLLMProvider,
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
    "openai-compatible": OpenAICompatibleProvider,
}


def get_provider(name: str, *, use_mock: bool = True) -> BaseModelProvider:
    cls = _PROVIDERS.get(name.lower(), LiteLLMProvider)
    return cls(use_mock=use_mock)


def list_providers() -> list[str]:
    return sorted(_PROVIDERS)


__all__ = [
    "ModelProvider",
    "MockCompletionResult",
    "BaseModelProvider",
    "LiteLLMProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "LMStudioProvider",
    "get_provider",
    "list_providers",
    "_derive_provider",
]
