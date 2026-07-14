from supervisor.adapters.langgraph.adapter import LangGraphInstrumentedAdapter
from supervisor.contracts.events import EventType
from supervisor.contracts.task import TaskContract
from supervisor.sdk import Supervisor


class FakeGraph:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        self.calls += 1
        return {"ok": True}


def test_attach_wraps_invoke_and_emits_run_lifecycle() -> None:
    task = TaskContract(task_id="t", task="demo")
    s = Supervisor(task)
    g = FakeGraph()
    wrapped = LangGraphInstrumentedAdapter().attach(g, s, auto_run_lifecycle=True)
    out = wrapped.invoke({"x": 1})
    assert out == {"ok": True}
    types = [e.event_type for e in s.collector.events()]
    assert EventType.RUN_STARTED in types
    assert EventType.RUN_COMPLETED in types
