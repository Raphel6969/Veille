from supervisor.adapters.langgraph.port import LangGraphAdapter
from supervisor.adapters.langgraph.stub import LangGraphAdapterStub


def test_stub_implements_adapter_protocol() -> None:
    stub = LangGraphAdapterStub()
    assert isinstance(stub, LangGraphAdapter)


def test_stub_returns_graph_unchanged() -> None:
    stub = LangGraphAdapterStub()

    class FakeHook:
        def on_run_started(self, run_id: str, task_id: str, metadata: dict) -> None: ...

        def on_run_finished(self, run_id: str, status: str, metadata: dict) -> None: ...

        def on_agent_event(
            self, run_id: str, agent_id: str, event_type: str, metadata: dict
        ) -> None: ...

        def on_tool_event(
            self,
            run_id: str,
            tool_name: str,
            event_type: str,
            input_data: dict,
            metadata: dict,
        ) -> None: ...

        def on_model_event(
            self,
            run_id: str,
            model_name: str,
            event_type: str,
            token_usage: dict,
            metadata: dict,
        ) -> None: ...

        def flush(self) -> list: ...

    graph = object()
    assert stub.attach(graph, FakeHook()) is graph


def test_extract_run_id_from_config() -> None:
    stub = LangGraphAdapterStub()
    run_id = stub.extract_run_id({"configurable": {"run_id": "fixed-id"}})
    assert run_id == "fixed-id"
