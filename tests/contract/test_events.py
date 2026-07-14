from datetime import UTC, datetime

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch


def test_run_event_round_trip() -> None:
    event = RunEvent(
        event_id="e1",
        run_id="r1",
        event_type=EventType.TOOL_COMPLETED,
        timestamp=datetime.now(UTC),
        tool_name="search_competitors",
        attributes={"normalized_input_hash": "abc123"},
    )
    restored = RunEvent.model_validate(event.model_dump(mode="json"))
    assert restored.event_type == EventType.TOOL_COMPLETED
    assert restored.normalized_input_hash() == "abc123"


def test_run_event_batch_schema_version() -> None:
    batch = RunEventBatch(run_id="r1", task_id="t1", events=[])
    assert batch.schema_version == "0.1.0"
