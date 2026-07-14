from supervisor.adapters.openai_responses.adapter import OpenAIResponsesAdapter
from supervisor.contracts.task import TaskContract
from supervisor.sdk import Supervisor


def test_adapter_has_correct_name() -> None:
    adapter = OpenAIResponsesAdapter()
    assert adapter.name == "openai_responses"


def test_adapter_implements_attach() -> None:
    adapter = OpenAIResponsesAdapter()
    task = TaskContract(task_id="t", task="test")
    supervisor = Supervisor(task)

    def fake_agent(input: object, sup: object) -> dict:
        return {"ok": True}

    wrapped = adapter.attach(fake_agent, supervisor)
    result = wrapped.invoke({"query": "hello"})
    assert result == {"ok": True}


def test_adapter_extract_run_id() -> None:
    adapter = OpenAIResponsesAdapter()
    rid = adapter.extract_run_id({"configurable": {"run_id": "abc-123"}})
    assert rid == "abc-123"
