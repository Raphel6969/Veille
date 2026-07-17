import uuid

from supervisor.console.explorer import explore
from supervisor.contracts.events import EventType, RunEvent, RunEventBatch


def _make_batch(run_id: str = "test-run") -> RunEventBatch:
    events = [
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_1",
            agent_id="agent_1",
            event_type=EventType.RUN_STARTED,
            attributes={"tier": "standard", "workflow": "test"},
        ),
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_1",
            agent_id="agent_1",
            event_type=EventType.MODEL_REQUESTED,
            attributes={"model": "gpt-4o", "provider": "openai", "match_type": "exact"},
        ),
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_1",
            agent_id="agent_1",
            event_type=EventType.MODEL_COMPLETED,
            attributes={"model": "gpt-4o", "reuse_reason": "served:exact+approved"},
        ),
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_1",
            agent_id="agent_1",
            event_type=EventType.TOOL_REQUESTED,
            attributes={"tool": "search", "match_type": "semantic"},
        ),
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_1",
            agent_id="agent_1",
            event_type=EventType.TOOL_COMPLETED,
            attributes={"tool": "search", "reuse_reason": "served:exact"},
        ),
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_1",
            agent_id="agent_1",
            event_type=EventType.VALIDATION_COMPLETED,
            status="passed",
            attributes={"checks": []},
        ),
        RunEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="step_2",
            agent_id="agent_2",
            event_type=EventType.RUN_COMPLETED,
            attributes={"result": "pass"},
        ),
    ]
    return RunEventBatch(run_id=run_id, task_id="test-task", events=events)


class TestExplore:
    def test_basic_timeline(self) -> None:
        batch = _make_batch()
        view = explore(batch)
        assert view["run_id"] == "test-run"
        assert len(view["timeline"]) == 7
        assert view["summary"]["total_cost_usd"] == 0.0

    def test_cache_view(self) -> None:
        batch = _make_batch()
        view = explore(batch)
        assert "served" in view["cache"]
        assert "misses" in view["cache"]

    def test_providers_list(self) -> None:
        batch = _make_batch()
        view = explore(batch)
        assert "openai" in view["providers"]

    def test_validation_results(self) -> None:
        batch = _make_batch()
        view = explore(batch)
        assert view["validation"] is not None
        assert view["validation"]["status"] == "passed"

    def test_trace_attributes_redact_prompts_and_credentials(self) -> None:
        batch = _make_batch()
        batch.events[1].attributes.update(
            {"raw_prompt": "private instruction", "nested": {"api_token": "secret-value"}}
        )

        view = explore(batch)
        attributes = view["timeline"][1]["attributes"]

        assert attributes["raw_prompt"] == "[REDACTED]"
        assert attributes["nested"]["api_token"] == "[REDACTED]"
