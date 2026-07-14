import uuid

from supervisor.adapters.generic import GenericFrameworkAdapter


class TestGenericAdapter:
    def test_attach_returns_instrumented_agent(self) -> None:
        adapter = GenericFrameworkAdapter()
        agent = adapter.attach("hello", None)  # type: ignore[arg-type]
        assert agent is not None
        assert hasattr(agent, "run")

    def test_extract_run_id_from_config(self) -> None:
        adapter = GenericFrameworkAdapter()
        rid = str(uuid.uuid4())
        config = {"run_id": rid}
        assert adapter.extract_run_id(config) == rid

    def test_extract_run_id_from_configurable(self) -> None:
        adapter = GenericFrameworkAdapter()
        rid = str(uuid.uuid4())
        config = {"configurable": {"run_id": rid}}
        assert adapter.extract_run_id(config) == rid

    def test_extract_run_id_none(self) -> None:
        adapter = GenericFrameworkAdapter()
        rid = adapter.extract_run_id(None)
        assert isinstance(rid, str)
        assert uuid.UUID(rid)
