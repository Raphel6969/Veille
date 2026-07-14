"""LangGraph adapter implementation (Phase 1).

Wraps a compiled LangGraph graph so that a supervised run is captured
automatically: run lifecycle via the wrapper, and model/tool/retry events via
a LangChain callback handler for graphs that use LangChain-native LLM/Tool
primitives. The cited-market-research demo uses the ``Supervisor`` helpers for
its manual mock calls, so the callback handler is dormant there but available
for any LangChain-based agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler

from supervisor.contracts.events import EventType

if TYPE_CHECKING:
    from supervisor.sdk.supervisor import Supervisor


class LangGraphCallbackHandler(BaseCallbackHandler):
    """Maps LangChain callback events to normalized supervisor ``RunEvent`` facts."""

    def __init__(self, supervisor: Supervisor) -> None:
        super().__init__()
        self._supervisor = supervisor

    def on_llm_start(
        self, serialized: Any, prompts: Any, *, run_id: Any = None, **kwargs: Any
    ) -> None:
        invocation = kwargs.get("invocation_params") or {}
        model = invocation.get("model") or invocation.get("model_name") or "unknown"
        preview = ""
        if isinstance(prompts, (list, tuple)) and prompts:
            preview = str(prompts[0])[:120]
        self._supervisor.collector.emit(
            EventType.MODEL_REQUESTED,
            model_name=str(model),
            attributes={"prompt_preview": preview},
        )

    def on_llm_end(self, response: Any, *, run_id: Any = None, **kwargs: Any) -> None:
        tokens_in = tokens_out = None
        try:
            usage = getattr(response, "llm_output", {}) or {}
            token_usage = usage.get("token_usage", {}) or {}
            tokens_in = token_usage.get("prompt_tokens")
            tokens_out = token_usage.get("completion_tokens")
        except Exception:
            pass
        self._supervisor.collector.emit(
            EventType.MODEL_COMPLETED,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            status="ok",
        )

    def on_tool_start(
        self, serialized: Any, input_str: Any, *, run_id: Any = None, **kwargs: Any
    ) -> None:
        name = (
            serialized.get("name")
            if isinstance(serialized, dict)
            else getattr(serialized, "name", None)
        )
        self._supervisor.collector.emit(
            EventType.TOOL_REQUESTED,
            tool_name=name,
            attributes={"input": {"input": str(input_str)[:500]}},
        )

    def on_tool_end(self, output: Any, *, run_id: Any = None, **kwargs: Any) -> None:
        self._supervisor.collector.emit(EventType.TOOL_COMPLETED, status="ok")

    def on_tool_error(self, error: Any, *, run_id: Any = None, **kwargs: Any) -> None:
        self._supervisor.collector.emit(
            EventType.TOOL_COMPLETED,
            status="error",
            error_message=str(error)[:500],
        )

    def on_retry(self, retry_state: Any, *, run_id: Any = None, **kwargs: Any) -> None:
        self._supervisor.collector.emit(EventType.RETRY_SCHEDULED)


class InstrumentedGraph:
    """A compiled graph wrapped so supervisor run lifecycle is captured."""

    def __init__(
        self, graph: Any, supervisor: Supervisor, *, auto_run_lifecycle: bool = True
    ) -> None:
        self._graph = graph
        self._supervisor = supervisor
        self._handler = LangGraphCallbackHandler(supervisor)
        self._auto = auto_run_lifecycle

    def _merge_config(self, config: Any) -> dict[str, Any]:
        base: dict[str, Any] = dict(config) if isinstance(config, dict) else {}
        callbacks = list(base.get("callbacks") or [])
        callbacks.append(self._handler)
        base["callbacks"] = callbacks
        return base

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        if self._auto:
            self._supervisor.start_run()
        try:
            out = self._graph.invoke(input, config=self._merge_config(config), **kwargs)
        except Exception:
            if self._auto:
                self._supervisor.finish_run("error")
            raise
        if self._auto:
            self._supervisor.finish_run("ok")
        return out


class LangGraphInstrumentedAdapter:
    """Phase 1 LangGraph adapter: implements the port's ``attach`` contract."""

    def attach(
        self, graph: Any, supervisor: Supervisor, *, auto_run_lifecycle: bool = True
    ) -> InstrumentedGraph:
        return InstrumentedGraph(graph, supervisor, auto_run_lifecycle=auto_run_lifecycle)

    def extract_run_id(self, config: dict[str, Any] | None) -> str:
        if config and "configurable" in config:
            run_id = config["configurable"].get("run_id")
            if isinstance(run_id, str):
                return run_id
        return str(uuid4())
