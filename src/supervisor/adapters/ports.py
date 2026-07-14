"""Framework-neutral adapter ports.

Generalizes framework-specific adapter contracts so every future agent framework
(CrewAI, AutoGen, Semantic Kernel, Mastra, PydanticAI, custom Python agents)
implements the same interface. Adapters turn framework-native lifecycle into
normalized ``RunEvent``s through the ``Supervisor`` runtime.

**Architecture rule:** Every adapter communicates only with ``Supervisor`` — the
central runtime abstraction. The ``Supervisor`` internally owns an event bus and
hook system, but adapters must not depend on those implementation details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from supervisor.sdk.supervisor import Supervisor


@runtime_checkable
class FrameworkAdapter(Protocol):
    """Port for wrapping any agent framework with supervisor instrumentation."""

    def attach(self, graph: Any, supervisor: Supervisor) -> Any:
        """Return an instrumented graph/agent bound to the supervisor runtime."""
        ...

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        """Extract or generate a stable run identifier."""
        ...
