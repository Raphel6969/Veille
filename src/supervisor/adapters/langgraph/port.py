"""LangGraph adapter port — Phase 1 will implement full instrumentation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from supervisor.contracts.events import RunEvent


@runtime_checkable
class LangGraphEventHook(Protocol):
    """Callback surface for LangGraph lifecycle events."""

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
class LangGraphAdapter(Protocol):
    """Port for wrapping LangGraph agents with supervisor instrumentation."""

    def attach(self, graph: Any, hook: LangGraphEventHook) -> Any:
        """Return an instrumented graph. Phase 1 implementation."""
        ...

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        """Extract or generate a stable run identifier."""
        ...
