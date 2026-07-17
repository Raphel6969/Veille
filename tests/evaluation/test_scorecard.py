from __future__ import annotations

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch
from supervisor.evaluation import sanitize_batch, scorecard


def _batch(run_id: str, *, cost: float, validation: str) -> RunEventBatch:
    return RunEventBatch(
        run_id=run_id,
        task_id="pilot-task",
        events=[
            RunEvent(event_id=f"{run_id}-start", run_id=run_id, event_type=EventType.RUN_STARTED),
            RunEvent(
                event_id=f"{run_id}-model",
                run_id=run_id,
                event_type=EventType.MODEL_COMPLETED,
                cost_usd=cost,
            ),
            RunEvent(
                event_id=f"{run_id}-validation",
                run_id=run_id,
                event_type=EventType.VALIDATION_COMPLETED,
                status=validation,
            ),
            RunEvent(event_id=f"{run_id}-done", run_id=run_id, event_type=EventType.RUN_COMPLETED),
        ],
    )


def test_scorecard_claims_savings_only_when_validation_is_preserved() -> None:
    baseline = _batch("baseline", cost=1.0, validation="pass")
    supervised = _batch("supervised", cost=0.4, validation="pass")

    result = scorecard(baseline, supervised)

    assert result.validation_preserved is True
    assert result.claimed_savings_usd == 0.6
    assert result.savings_blocked_reason is None


def test_scorecard_blocks_savings_when_validation_regresses() -> None:
    baseline = _batch("baseline", cost=1.0, validation="pass")
    supervised = _batch("supervised", cost=0.4, validation="failed")

    result = scorecard(baseline, supervised)

    assert result.validation_preserved is False
    assert result.claimed_savings_usd == 0.0
    assert result.savings_blocked_reason is not None


def test_sanitize_batch_redacts_nested_sensitive_trace_fields() -> None:
    batch = _batch("trace", cost=0.1, validation="pass")
    batch.events[1].attributes = {
        "prompt_preview": "do not export",
        "nested": {"api_token": "do not export"},
        "safe": "retain",
    }

    sanitized = sanitize_batch(batch)
    attributes = sanitized.events[1].attributes

    assert attributes["prompt_preview"] == "[REDACTED]"
    assert attributes["nested"]["api_token"] == "[REDACTED]"
    assert attributes["safe"] == "retain"
