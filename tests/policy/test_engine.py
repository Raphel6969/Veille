from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch
from supervisor.policy import evaluate_observe


def _ev(
    event_type: EventType, tool_name: str | None = None, hash: str | None = None, status: str = "ok"
) -> RunEvent:
    attrs: dict = {}
    if hash is not None:
        attrs["normalized_input_hash"] = hash
    if status == "error":
        attrs["failed"] = True
    return RunEvent(
        event_id=str(uuid4()),
        run_id="r",
        event_type=event_type,
        tool_name=tool_name,
        status=status,
        attributes=attrs,
    )


def test_duplicate_after_success_triggers() -> None:
    batch = RunEventBatch(
        run_id="r",
        task_id="t",
        events=[
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
        ],
    )
    triggers, _ = evaluate_observe(batch)
    assert any(t.policy_id == "duplicate_tool_protection" for t in triggers)


def test_duplicate_after_failure_is_recovery_not_flagged() -> None:
    batch = RunEventBatch(
        run_id="r",
        task_id="t",
        events=[
            _ev(EventType.TOOL_COMPLETED, "t", "h", "error"),
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
        ],
    )
    triggers, _ = evaluate_observe(batch)
    assert all(t.policy_id != "duplicate_tool_protection" for t in triggers)


def test_retry_budget_triggers() -> None:
    batch = RunEventBatch(
        run_id="r",
        task_id="t",
        events=[_ev(EventType.RETRY_SCHEDULED) for _ in range(6)],
    )
    triggers, _ = evaluate_observe(batch)
    assert any(t.policy_id == "retry_budget" for t in triggers)


def test_observe_only_appends_events_with_action_observe() -> None:
    batch = RunEventBatch(
        run_id="r",
        task_id="t",
        events=[
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
        ],
    )
    triggers, extra = evaluate_observe(batch)
    types = [e.event_type for e in extra]
    assert EventType.POLICY_TRIGGERED in types
    assert EventType.INTERVENTION_APPLIED in types
    assert all(
        e.attributes.get("action") == "observe"
        for e in extra
        if e.event_type == EventType.INTERVENTION_APPLIED
    )
    # Observe-only must not mutate the original run events.
    assert len(batch.events) == 2
