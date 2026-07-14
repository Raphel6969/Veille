"""LangGraph adapter stub — returns graph unchanged until full instrumentation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from supervisor.sdk.supervisor import Supervisor


class LangGraphAdapterStub:
    """Stub: returns the graph unchanged. Placeholder until full instrumentation."""

    def attach(self, graph: Any, supervisor: Supervisor) -> Any:
        _ = supervisor
        return graph

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        if config and "configurable" in config:
            run_id = config["configurable"].get("run_id")
            if isinstance(run_id, str):
                return run_id
        return str(uuid4())


# LangGraphAdapterStub implements the LangGraphAdapter protocol.
