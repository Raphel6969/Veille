"""Generic framework adapter base.

Wraps any Python agent/callable so it executes *through* Veille's runtime and
emits normalized events. OpenAI Agents SDK and OpenAI Responses API adapters
build on this; SDK-specific tracing hooks (handoffs, traces) are future
integration points layered on top of ``InstrumentedAgent``.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from supervisor.sdk import Supervisor


@runtime_checkable
class FrameworkAgent(Protocol):
    def run(self, input: Any, **kwargs: Any) -> Any: ...
    def invoke(self, input: Any, **kwargs: Any) -> Any: ...


class InstrumentedAgent:
    """Runs an agent callable under Veille's run lifecycle."""

    def __init__(self, agent_fn: Any, supervisor: Supervisor) -> None:
        self._agent_fn = agent_fn
        self._supervisor = supervisor

    def run(self, input: Any, **kwargs: Any) -> Any:
        self._supervisor.start_run()
        try:
            result = self._agent_fn(input, self._supervisor)
        except Exception:
            self._supervisor.finish_run("error")
            raise
        self._supervisor.finish_run("pass")
        return result

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        return self.run(input, **kwargs)


class GenericFrameworkAdapter:
    """Implements the framework-neutral :class:`FrameworkAdapter` port."""

    def attach(self, target: Any, supervisor: Supervisor, **kwargs: Any) -> InstrumentedAgent:
        return InstrumentedAgent(target, supervisor)

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        if config and config.get("run_id"):
            return str(config["run_id"])
        if config and config.get("configurable", {}).get("run_id"):
            return str(config["configurable"]["run_id"])
        return str(uuid.uuid4())
