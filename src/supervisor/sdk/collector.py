"""In-process collector for normalized supervisor run events (Phase 1 SDK)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch


class RunCollector:
    """Collects ``RunEvent`` facts for a single run and emits a batch for replay."""

    def __init__(self, run_id: str, task_id: str) -> None:
        self.run_id = run_id
        self.task_id = task_id
        self._events: list[RunEvent] = []
        self._clock = datetime.now(UTC)

    def _tick(self, ms: float = 50.0) -> datetime:
        self._clock += timedelta(milliseconds=ms)
        return self._clock

    def emit(
        self,
        event_type: EventType,
        *,
        step_id: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        model_name: str | None = None,
        duration_ms: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        status: str | None = None,
        error_message: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> RunEvent:
        event = RunEvent(
            event_id=str(uuid4()),
            run_id=self.run_id,
            event_type=event_type,
            timestamp=self._tick(duration_ms or 50.0),
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            model_name=model_name,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            status=status,
            error_message=error_message,
            attributes=attributes or {},
        )
        self._events.append(event)
        return event

    def append(self, event: RunEvent) -> None:
        self._events.append(event)

    def events(self) -> list[RunEvent]:
        return list(self._events)

    def to_batch(self, metadata: dict[str, Any] | None = None) -> RunEventBatch:
        return RunEventBatch(
            run_id=self.run_id,
            task_id=self.task_id,
            events=list(self._events),
            metadata=metadata or {},
        )
