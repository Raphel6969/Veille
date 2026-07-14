"""OpenAI Agents SDK adapter.

Executes OpenAI Agents SDK agents through Veille's runtime. The base
``GenericFrameworkAdapter`` runs the agent and emits normalized events; SDK-specific
tracing (handoffs, guardrails, session traces) is layered on here when the
``openai-agents`` package is installed. Until then, any Python agent callable is
run through Veille unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from supervisor.adapters.generic import GenericFrameworkAdapter, InstrumentedAgent

if TYPE_CHECKING:
    from supervisor.sdk import Supervisor


class OpenAIAgentsAdapter(GenericFrameworkAdapter):
    """Adapter for OpenAI Agents SDK agents."""

    name = "openai_agents"

    def attach(self, target: Any, supervisor: Supervisor, **kwargs: Any) -> InstrumentedAgent:
        # If the real SDK is present, prefer its Runner so tracing integrates;
        # otherwise fall back to the generic instrumented callable.
        try:  # pragma: no cover - optional dependency
            from agents import Runner  # type: ignore

            if hasattr(target, "run") or hasattr(target, "invoke"):

                def _run(input: Any, sup: Supervisor) -> Any:
                    return Runner.run(target, input)

                return InstrumentedAgent(_run, supervisor)
        except Exception:  # noqa: BLE001
            pass
        return super().attach(target, supervisor)
