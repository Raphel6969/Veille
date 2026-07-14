"""Framework-neutral adapter ports.

Generalizes the LangGraph-specific port pair into provider-agnostic contracts so
every future agent framework (CrewAI, AutoGen, Semantic Kernel, Mastra, PydanticAI,
custom Python agents) implements the same interface. Adapters turn framework-native
lifecycle into normalized ``RunEvent``s through the supervisor's collector.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from supervisor.contracts.events import RunEvent


@runtime_checkable
class RunEventHook(Protocol):
    """Sink for normalized runtime events emitted by any framework adapter."""

    def on_run_started(self, run_id: str, task_id: str, metadata: dict[str, Any]) -> None: ...

    def on_run_finished(self, run_id: str, status: str, metadata: dict[str, Any]) -> None: ...

    def on_agent_event(
        self, run_id: str, agent_id: str, event_type: str, metadata: dict[str, Any]
    ) -> None: ...

    def on_tool_event(
        self,
        run_id: str,
        tool_name: str,
        event_type: str,
        input_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None: ...

    def on_model_event(
        self,
        run_id: str,
        model_name: str,
        event_type: str,
        token_usage: dict[str, int],
        metadata: dict[str, Any],
    ) -> None: ...

    def flush(self) -> list[RunEvent]: ...


@runtime_checkable
class FrameworkAdapter(Protocol):
    """Port for wrapping any agent framework with supervisor instrumentation."""

    def attach(self, graph: Any, hook: RunEventHook) -> Any:
        """Return an instrumented graph/agent bound to the hook."""
        ...

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        """Extract or generate a stable run identifier."""
        ...
