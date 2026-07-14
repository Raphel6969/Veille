"""LangGraph adapter stub — returns graph unchanged until Phase 1."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from supervisor.adapters.langgraph.port import LangGraphEventHook


class LangGraphAdapterStub:
    """Phase 0 stub: documents the adapter contract without modifying execution."""

    def attach(self, graph: Any, hook: LangGraphEventHook) -> Any:
        _ = hook
        return graph

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        if config and "configurable" in config:
            run_id = config["configurable"].get("run_id")
            if isinstance(run_id, str):
                return run_id
        return str(uuid4())


# LangGraphAdapterStub implements the LangGraphAdapter protocol.
