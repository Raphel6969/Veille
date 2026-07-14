"""LangGraph adapter port — defines the contract for LangGraph instrumentation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from supervisor.sdk.supervisor import Supervisor


@runtime_checkable
class LangGraphAdapter(Protocol):
    """Port for wrapping LangGraph agents with supervisor instrumentation."""

    def attach(self, graph: Any, supervisor: Supervisor) -> Any:
        """Return an instrumented graph bound to the supervisor runtime."""
        ...

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        """Extract or generate a stable run identifier."""
        ...
