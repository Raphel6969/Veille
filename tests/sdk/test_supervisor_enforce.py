import pytest

from supervisor.contracts.events import EventType
from supervisor.contracts.task import TaskContract
from supervisor.policy import StopRun
from supervisor.sdk import Supervisor


def _task() -> TaskContract:
    return TaskContract(task_id="t", task="demo")


def test_enforce_dedupes_duplicate_tool_call() -> None:
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "value"

    s = Supervisor(_task(), enforce=True)
    s.tool(step_id="s", agent_id="a", tool_name="tool", input={}, fn=fn, normalized_input_hash="h")
    r2 = s.tool(
        step_id="s", agent_id="a", tool_name="tool", input={}, fn=fn, normalized_input_hash="h"
    )
    # The second call must not execute the external function; it returns the cache.
    assert calls["n"] == 1
    assert r2 == "value"
    events = s.collector.events()
    assert any(e.status == "blocked" for e in events if e.event_type == EventType.TOOL_COMPLETED)
    assert any(e.event_type == EventType.INTERVENTION_APPLIED for e in events)


def test_safe_default_does_not_change_behavior() -> None:
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "value"

    s = Supervisor(_task(), enforce=False)
    s.tool(step_id="s", agent_id="a", tool_name="tool", input={}, fn=fn, normalized_input_hash="h")
    s.tool(step_id="s", agent_id="a", tool_name="tool", input={}, fn=fn, normalized_input_hash="h")
    assert calls["n"] == 2
    events = s.collector.events()
    assert not any(e.event_type == EventType.INTERVENTION_APPLIED for e in events)
    assert all(e.status == "ok" for e in events if e.event_type == EventType.TOOL_COMPLETED)


def test_enforce_retry_budget_stops_run() -> None:
    s = Supervisor(_task(), enforce=True)
    with pytest.raises(StopRun):
        for _ in range(s._budget.retry_limit + 2):
            s.retry(
                step_id="s",
                agent_id="a",
                tool_name="fetch",
                competitor="acme",
                attempt=1,
            )


def test_enforce_emits_intervention_on_stop() -> None:
    s = Supervisor(_task(), enforce=True)
    with pytest.raises(StopRun):
        while True:
            s.retry(
                step_id="s",
                agent_id="a",
                tool_name="fetch",
                competitor="acme",
                attempt=1,
            )
    assert any(e.event_type == EventType.INTERVENTION_APPLIED for e in s.collector.events())
