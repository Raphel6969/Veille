"""Phase 1 Supervisor SDK: typed helpers that emit normalized run events.

The SDK makes an agent run inspectable without changing its business logic.
Application code (or a deeper framework adapter) calls these helpers around
model/tool/context/retry work; the SDK records normalized ``RunEvent`` facts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from supervisor.contracts.events import EventType, RunEventBatch
from supervisor.contracts.task import TaskContract
from supervisor.sdk.collector import RunCollector


class Supervisor:
    """Owns one supervised run: an event collector plus typed emit helpers."""

    def __init__(self, task_contract: TaskContract) -> None:
        self.task_contract = task_contract
        self.task_id = task_contract.task_id
        self.run_id = str(uuid4())
        self.scenario: str | None = None
        self._collector = RunCollector(self.run_id, self.task_id)

    @property
    def collector(self) -> RunCollector:
        return self._collector

    # -- run lifecycle -----------------------------------------------------

    def start_run(self) -> None:
        attributes: dict[str, Any] = {"task": self.task_contract.task}
        if self.scenario is not None:
            attributes["scenario"] = self.scenario
        self._collector.emit(EventType.RUN_STARTED, attributes=attributes)

    def finish_run(self, status: str) -> None:
        duplicates = sum(
            1
            for e in self._collector.events()
            if e.event_type == EventType.TOOL_COMPLETED and e.attributes.get("duplicate")
        )
        retries = sum(
            1 for e in self._collector.events() if e.event_type == EventType.RETRY_SCHEDULED
        )
        self._collector.emit(
            EventType.RUN_COMPLETED,
            status=status,
            attributes={"duplicate_search_count": duplicates, "retry_count": retries},
        )

    def emit_validation(self, report: Any) -> None:
        self._collector.emit(
            EventType.VALIDATION_COMPLETED,
            status="pass" if report.task_contract_met else "fail",
            attributes={"checks": [c.model_dump() for c in report.checks]},
        )

    # -- agent / step lifecycle -------------------------------------------

    @contextmanager
    def node(self, *, step_id: str, agent_id: str, role: str) -> Iterator[None]:
        self._collector.emit(
            EventType.AGENT_STARTED,
            step_id=step_id,
            agent_id=agent_id,
            attributes={"role": role},
        )
        try:
            yield
        finally:
            self._collector.emit(
                EventType.AGENT_FINISHED,
                step_id=step_id,
                agent_id=agent_id,
                status="ok",
            )

    # -- model call --------------------------------------------------------

    def model(
        self,
        *,
        step_id: str,
        agent_id: str,
        model: str,
        prompt: str,
        adapter: Any,
    ) -> str:
        self._collector.emit(
            EventType.MODEL_REQUESTED,
            step_id=step_id,
            agent_id=agent_id,
            model_name=model,
            attributes={"prompt_preview": prompt[:120]},
        )
        result = adapter.complete(model, prompt)
        self._collector.emit(
            EventType.MODEL_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            model_name=model,
            duration_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            status="ok",
        )
        return str(result.content)

    # -- tool call ---------------------------------------------------------

    def tool(
        self,
        *,
        step_id: str,
        agent_id: str,
        tool_name: str,
        input: dict[str, Any],
        fn: Callable[[], Any],
        normalized_input_hash: str | None = None,
        duplicate: bool = False,
        failed: bool = False,
        duration_ms: float | None = None,
        cost_usd: float | None = None,
        status: str = "ok",
        error_message: str | None = None,
    ) -> Any:
        attributes: dict[str, Any] = {"input": input}
        if normalized_input_hash is not None:
            attributes["normalized_input_hash"] = normalized_input_hash
        if duplicate:
            attributes["duplicate"] = True
        if failed:
            attributes["failed"] = True
        self._collector.emit(
            EventType.TOOL_REQUESTED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            attributes=attributes,
        )
        result = fn()
        self._collector.emit(
            EventType.TOOL_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            status=status,
            error_message=error_message if failed else None,
            attributes=attributes,
        )
        return result

    # -- retry -------------------------------------------------------------

    def retry(
        self,
        *,
        step_id: str,
        agent_id: str,
        tool_name: str,
        competitor: str,
        attempt: int,
    ) -> None:
        self._collector.emit(
            EventType.RETRY_SCHEDULED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            attributes={"competitor": competitor, "attempt": attempt},
        )
        self._collector.emit(
            EventType.RETRY_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            attributes={"competitor": competitor, "attempt": attempt + 1},
        )

    # -- context manifest --------------------------------------------------

    def context(
        self,
        *,
        step_id: str,
        agent_id: str,
        role: str,
        included: list[str],
        excluded: list[str],
        compressed: list[str],
        estimated_tokens: int,
        reason: str,
    ) -> None:
        self._collector.emit(
            EventType.CONTEXT_ATTACHED,
            step_id=step_id,
            agent_id=agent_id,
            attributes={
                "role": role,
                "included": included,
                "excluded": excluded,
                "compressed": compressed,
                "estimated_tokens": estimated_tokens,
                "reason": reason,
            },
        )

    # -- batch -------------------------------------------------------------

    def to_batch(self, metadata: dict[str, Any] | None = None) -> RunEventBatch:
        return self._collector.to_batch(metadata=metadata)
