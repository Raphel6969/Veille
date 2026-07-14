from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.contracts.events import EventType
from supervisor.contracts.task import TaskContract
from supervisor.sdk import Supervisor


def _task() -> TaskContract:
    return TaskContract(task_id="t1", task="demo")


def test_model_emits_requested_and_completed() -> None:
    s = Supervisor(_task())
    content = s.model(
        step_id="s",
        agent_id="a",
        model="mock-research",
        prompt="p",
        adapter=LiteLLMMockAdapter(use_mock=True),
    )
    types = [e.event_type for e in s.collector.events()]
    assert EventType.MODEL_REQUESTED in types
    assert EventType.MODEL_COMPLETED in types
    assert content.startswith("[mock")


def test_tool_preserves_duplicate_attribute_on_completed() -> None:
    s = Supervisor(_task())
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="t",
        input={"x": 1},
        fn=lambda: "r",
        normalized_input_hash="h",
        duplicate=True,
    )
    completed = [e for e in s.collector.events() if e.event_type == EventType.TOOL_COMPLETED][0]
    assert completed.attributes.get("duplicate") is True
    assert completed.normalized_input_hash() == "h"


def test_retry_emits_scheduled_and_completed() -> None:
    s = Supervisor(_task())
    s.retry(step_id="s", agent_id="a", tool_name="t", competitor="c", attempt=1)
    types = [e.event_type for e in s.collector.events()]
    assert EventType.RETRY_SCHEDULED in types
    assert EventType.RETRY_COMPLETED in types


def test_context_emits_attached() -> None:
    s = Supervisor(_task())
    s.context(
        step_id="s",
        agent_id="a",
        role="researcher",
        included=["q"],
        excluded=["x"],
        compressed=["y"],
        estimated_tokens=10,
        reason="r",
    )
    evs = [e for e in s.collector.events() if e.event_type == EventType.CONTEXT_ATTACHED]
    assert len(evs) == 1
    assert evs[0].attributes["role"] == "researcher"


def test_node_emits_agent_lifecycle() -> None:
    s = Supervisor(_task())
    with s.node(step_id="s", agent_id="a", role="r"):
        pass
    types = [e.event_type for e in s.collector.events()]
    assert EventType.AGENT_STARTED in types
    assert EventType.AGENT_FINISHED in types


def test_finish_run_counts_duplicates_and_retries() -> None:
    s = Supervisor(_task())
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="t",
        input={"x": 1},
        fn=lambda: 1,
        normalized_input_hash="h",
        duplicate=True,
    )
    s.retry(step_id="s", agent_id="a", tool_name="t", competitor="c", attempt=1)
    s.finish_run("ok")
    completed = [e for e in s.collector.events() if e.event_type == EventType.RUN_COMPLETED][0]
    assert completed.attributes["duplicate_search_count"] == 1
    assert completed.attributes["retry_count"] == 1
