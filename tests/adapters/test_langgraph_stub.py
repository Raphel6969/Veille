from supervisor.adapters.langgraph.port import LangGraphAdapter
from supervisor.adapters.langgraph.stub import LangGraphAdapterStub
from supervisor.contracts.task import TaskContract
from supervisor.sdk import Supervisor


def test_stub_implements_adapter_protocol() -> None:
    stub = LangGraphAdapterStub()
    assert isinstance(stub, LangGraphAdapter)


def test_stub_returns_graph_unchanged() -> None:
    stub = LangGraphAdapterStub()
    supervisor = Supervisor(TaskContract(task_id="t", task="stub test"))
    graph = object()
    assert stub.attach(graph, supervisor) is graph


def test_extract_run_id_from_config() -> None:
    stub = LangGraphAdapterStub()
    run_id = stub.extract_run_id({"configurable": {"run_id": "fixed-id"}})
    assert run_id == "fixed-id"
