from datetime import UTC, datetime, timedelta

import pytest

from supervisor.analytics import summarize
from supervisor.contracts.events import EventType, RunEvent, RunEventBatch


def _batch() -> RunEventBatch:
    start = datetime.now(UTC)
    events = [
        RunEvent(event_id="1", run_id="r", event_type=EventType.RUN_STARTED, timestamp=start),
        RunEvent(
            event_id="2",
            run_id="r",
            event_type=EventType.TOOL_COMPLETED,
            step_id="s",
            agent_id="a",
            tool_name="t",
            cost_usd=0.01,
            attributes={"normalized_input_hash": "h"},
        ),
        RunEvent(
            event_id="3",
            run_id="r",
            event_type=EventType.TOOL_COMPLETED,
            step_id="s",
            agent_id="a",
            tool_name="t",
            cost_usd=0.01,
            attributes={"normalized_input_hash": "h", "duplicate": True},
        ),
        RunEvent(
            event_id="4",
            run_id="r",
            event_type=EventType.RETRY_SCHEDULED,
            step_id="s",
            agent_id="a",
            tool_name="t",
        ),
        RunEvent(
            event_id="5",
            run_id="r",
            event_type=EventType.CONTEXT_ATTACHED,
            step_id="s",
            agent_id="a",
        ),
        RunEvent(
            event_id="6",
            run_id="r",
            event_type=EventType.MODEL_COMPLETED,
            step_id="s",
            agent_id="a",
            model_name="m",
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.02,
        ),
        RunEvent(
            event_id="7",
            run_id="r",
            event_type=EventType.RUN_COMPLETED,
            timestamp=start + timedelta(seconds=5),
        ),
    ]
    return RunEventBatch(
        run_id="r", task_id="t1", events=events, metadata={"scenario": "expensive"}
    )


def test_summarize_totals() -> None:
    s = summarize(_batch())
    assert s.total_cost_usd == pytest.approx(0.04)
    assert s.tool_calls == 2
    assert s.duplicates == 1
    assert s.retries == 1
    assert s.context_attached == 1
    assert s.model_calls == 1
    assert s.total_latency_s == pytest.approx(5.0)
    assert s.per_tool[0].duplicates == 1


def test_summarize_scenario_from_metadata() -> None:
    s = summarize(_batch())
    assert s.scenario == "expensive"
