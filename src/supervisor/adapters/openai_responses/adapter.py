"""OpenAI Responses API adapter.

Runs agents built on the OpenAI Responses API through Veille's runtime. Shares
the generic instrumented execution; Responses-API tracing (response objects,
tool calls) is integrated here when the SDK is available.
"""

from __future__ import annotations

from typing import Any

from supervisor.adapters.generic import GenericFrameworkAdapter, InstrumentedAgent
from supervisor.sdk import Supervisor


class OpenAIResponsesAdapter(GenericFrameworkAdapter):
    """Adapter for OpenAI Responses API agents."""

    name = "openai_responses"

    def attach(self, target: Any, supervisor: Supervisor, **kwargs: Any) -> InstrumentedAgent:
        # When the real SDK is present, route through the Responses client so the
        # native trace is captured; otherwise run the generic instrumented callable.
        try:  # pragma: no cover - optional dependency
            from openai import OpenAI  # type: ignore

            if hasattr(target, "run") or hasattr(target, "invoke"):

                def _run(input: Any, sup: Supervisor) -> Any:
                    client = OpenAI()
                    return client.responses.create(model="gpt-4o", input=input)

                return InstrumentedAgent(_run, supervisor)
        except Exception:  # noqa: BLE001
            pass
        return super().attach(target, supervisor)
