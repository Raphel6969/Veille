from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch
from supervisor.policy import evaluate
from supervisor.policy.engine import RETRY_BUDGET


def _ev(
    event_type: EventType,
    tool_name: str | None = None,
    hash: str | None = None,
    status: str = "ok",
    cost_usd: float | None = None,
    duration_ms: float | None = None,
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
        cost_usd=cost_usd,
        duration_ms=duration_ms,
        attributes=attrs,
    )


def _batch(events: list[RunEvent]) -> RunEventBatch:
    return RunEventBatch(run_id="r", task_id="t", events=events)


def test_observe_mode_never_applies_action() -> None:
    batch = _batch(
        [
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
        ]
    )
    decisions, _ = evaluate(batch, enforce=False)
    assert decisions
    assert all(d.action == "observe" for d in decisions)
    assert all(not d.applied for d in decisions)


def test_enforce_duplicate_blocks() -> None:
    batch = _batch(
        [
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
            _ev(EventType.TOOL_COMPLETED, "t", "h", "ok"),
        ]
    )
    decisions, events = evaluate(batch, enforce=True)
    dup = [d for d in decisions if d.policy_id == "duplicate_tool_protection"]
    assert dup and dup[0].action == "block" and dup[0].applied
    assert any(e.event_type == EventType.INTERVENTION_APPLIED for e in events)
    assert any(
        e.attributes.get("action") == "block"
        for e in events
        if e.event_type == EventType.INTERVENTION_APPLIED
    )


def test_enforce_retry_budget_stops() -> None:
    batch = _batch([_ev(EventType.RETRY_SCHEDULED) for _ in range(RETRY_BUDGET + 2)])
    decisions, _ = evaluate(batch, enforce=True)
    retry = [d for d in decisions if d.policy_id == "retry_budget"]
    assert retry and retry[0].action == "stop" and retry[0].applied


def test_enforce_cost_budget_stops() -> None:
    batch = _batch(
        [
            _ev(EventType.TOOL_COMPLETED, "t", "h", cost_usd=0.6),
            _ev(EventType.TOOL_COMPLETED, "t", "h2", cost_usd=0.6),
        ]
    )
    decisions, _ = evaluate(batch, enforce=True, max_cost_usd=1.0)
    cost = [d for d in decisions if d.policy_id == "cost_budget"]
    assert cost and cost[0].action == "stop"


def test_enforce_loop_protection_stops() -> None:
    batch = _batch([_ev(EventType.TOOL_COMPLETED, "t", "h", "ok") for _ in range(4)])
    decisions, _ = evaluate(batch, enforce=True)
    loop = [d for d in decisions if d.policy_id == "loop_protection"]
    assert loop and loop[0].action == "stop"


def test_human_review_required_for_pause() -> None:
    # pause/handoff actions would set human_review_required; stop does not.
    batch = _batch([_ev(EventType.RETRY_SCHEDULED) for _ in range(RETRY_BUDGET + 2)])
    decisions, _ = evaluate(batch, enforce=True)
    assert all(not d.human_review_required for d in decisions)
