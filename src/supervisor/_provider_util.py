"""Shared provider utility — breaks the SDK↔adapters circular dependency.

``_derive_provider`` is needed by both the SDK (for event metadata) and the
router (for routing decisions). Putting it in either ``sdk/`` or ``adapters/``
creates a bidirectional dependency. This module lives directly in ``supervisor/``
so either side can import it independently.
"""


def _derive_provider(model: str) -> str:
    m = model.lower()
    if m.startswith("openrouter/"):
        return "openrouter"
    if m.startswith("ollama/") or m.startswith("ollama"):
        return "ollama"
    if m.startswith("lmstudio"):
        return "lmstudio"
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "gemini" in m:
        return "gemini"
    if m.startswith("litellm/"):
        return "litellm"
    if m.startswith("gpt") or "openai" in m:
        return "openai"
    if m.startswith("mock"):
        return "mock"
    return "openai"


__all__ = ["_derive_provider"]
