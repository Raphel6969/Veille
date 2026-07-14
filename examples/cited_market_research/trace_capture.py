"""Capture normalized run events from synthetic workflow execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch
from supervisor.contracts.validation import CheckResult, ValidationReport


class TraceCapture:
    """Manual event collector used in Phase 0 before SDK instrumentation."""

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
    ) -> None:
        self._events.append(
            RunEvent(
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
        )

    def to_batch(self, metadata: dict[str, Any] | None = None) -> RunEventBatch:
        return RunEventBatch(
            run_id=self.run_id,
            task_id=self.task_id,
            events=self._events,
            metadata=metadata or {},
        )


def validate_brief(
    run_id: str,
    task_id: str,
    brief: dict[str, Any],
) -> ValidationReport:
    checks: list[CheckResult] = []

    fields_ok = brief.get("competitors_count", 0) >= 8 and bool(brief.get("comparison_table"))
    checks.append(
        CheckResult(
            check_id="required_fields_present",
            passed=fields_ok,
            message="Eight competitors and comparison table required.",
        )
    )

    citations_ok = all(row.get("source") for row in brief.get("comparison_table", []))
    checks.append(
        CheckResult(
            check_id="citations_valid",
            passed=citations_ok,
            message="Every material claim must have a linked source.",
        )
    )

    names = [row.get("competitor") for row in brief.get("comparison_table", [])]
    no_dups = len(names) == len(set(names))
    checks.append(
        CheckResult(
            check_id="no_duplicate_competitors",
            passed=no_dups,
            message="Competitor list must not contain duplicates.",
        )
    )

    passed = all(c.passed for c in checks)
    return ValidationReport(
        run_id=run_id,
        task_id=task_id,
        task_contract_met=passed,
        checks=checks,
        confidence=1.0 if passed else 0.4,
        unresolved_issues=[] if passed else ["validation_failed"],
    )
