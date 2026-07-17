"""Validation-gated pilot scorecards and safe trace exports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from supervisor.analytics import summarize
from supervisor.contracts.events import EventType, RunEventBatch

_SENSITIVE_PARTS = (
    "prompt",
    "payload",
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "api_key",
)
_REDACTED = "[REDACTED]"


def _sanitize(value: Any, *, key: str = "") -> Any:
    if any(part in key.lower().replace("-", "_") for part in _SENSITIVE_PARTS):
        return _REDACTED
    if isinstance(value, dict):
        return {str(k): _sanitize(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, key=key) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item, key=key) for item in value]
    return value


def sanitize_batch(batch: RunEventBatch) -> RunEventBatch:
    """Create a replayable batch without prompt or credential-shaped data."""
    events = [
        event.model_copy(
            update={
                "attributes": _sanitize(event.attributes),
                "error_message": _REDACTED if event.error_message else None,
            }
        )
        for event in batch.events
    ]
    return batch.model_copy(update={"events": events, "metadata": _sanitize(batch.metadata)})


def _validation_passed(batch: RunEventBatch) -> bool:
    return any(
        event.event_type == EventType.VALIDATION_COMPLETED and event.status in {"pass", "passed"}
        for event in batch.events
    )


def _false_interventions(batch: RunEventBatch) -> int:
    return sum(
        1
        for event in batch.events
        if event.event_type == EventType.INTERVENTION_APPLIED
        and event.attributes.get("false_positive") is True
    )


@dataclass(frozen=True)
class PilotScorecard:
    baseline_run_id: str
    supervised_run_id: str
    validation_preserved: bool
    baseline_cost_usd: float
    supervised_cost_usd: float
    cost_delta_usd: float
    claimed_savings_usd: float
    latency_delta_s: float
    false_interventions: int
    user_acceptance: bool | None
    savings_blocked_reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def scorecard(baseline: RunEventBatch, supervised: RunEventBatch) -> PilotScorecard:
    """Compare runs, withholding a savings claim unless validation is preserved."""
    baseline_summary = summarize(baseline)
    supervised_summary = summarize(supervised)
    validation_preserved = _validation_passed(baseline) and _validation_passed(supervised)
    cost_delta = round(baseline_summary.total_cost_usd - supervised_summary.total_cost_usd, 6)
    claimed_savings = max(0.0, cost_delta) if validation_preserved else 0.0
    acceptance = supervised.metadata.get("user_acceptance")
    user_acceptance = acceptance if isinstance(acceptance, bool) else None
    blocked_reason = None
    if not validation_preserved:
        blocked_reason = "Validation did not pass for both baseline and supervised runs."
    elif cost_delta <= 0:
        blocked_reason = "The supervised run did not cost less than the baseline."
    return PilotScorecard(
        baseline_run_id=baseline.run_id,
        supervised_run_id=supervised.run_id,
        validation_preserved=validation_preserved,
        baseline_cost_usd=baseline_summary.total_cost_usd,
        supervised_cost_usd=supervised_summary.total_cost_usd,
        cost_delta_usd=cost_delta,
        claimed_savings_usd=claimed_savings,
        latency_delta_s=round(
            baseline_summary.total_latency_s - supervised_summary.total_latency_s, 3
        ),
        false_interventions=_false_interventions(supervised),
        user_acceptance=user_acceptance,
        savings_blocked_reason=blocked_reason,
    )
