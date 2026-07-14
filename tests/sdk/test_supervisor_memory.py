from supervisor.analytics.run_summary import summarize
from supervisor.contracts.events import EventType
from supervisor.contracts.task import RiskLevel, TaskContract
from supervisor.memory import MemoryTier
from supervisor.sdk import Supervisor


def _task() -> TaskContract:
    return TaskContract(
        task_id="t",
        task="demo",
        risk_level=RiskLevel.MEDIUM,
        quality_checks=["citations_valid"],
    )


def _events(s: Supervisor, et: EventType):
    return [e for e in s.collector.events() if e.event_type == et]


def test_memory_disabled_is_passthrough() -> None:
    s = Supervisor(_task())
    s.start_run()
    out = s.retrieve_memory(step_id="s", agent_id="a", role="researcher", query="x")
    assert out == []
    reqs = _events(s, EventType.MEMORY_RETRIEVED)
    assert len(reqs) == 1
    assert reqs[0].attributes.get("included") == []


def test_remember_and_retrieve_emits_manifest() -> None:
    s = Supervisor(_task(), memory=True)
    s.start_run()
    s.remember(step_id="s", agent_id="a", content="evidence about X", tier=MemoryTier.LONG)
    out = s.retrieve_memory(step_id="s", agent_id="a", role="researcher", query="evidence")
    assert len(out) == 1
    req = _events(s, EventType.MEMORY_RETRIEVED)[0]
    assert req.attributes["included"]
    assert req.attributes["role"] == "researcher"


def test_summary_reports_memories() -> None:
    s = Supervisor(_task(), memory=True)
    s.start_run()
    s.remember(step_id="s", agent_id="a", content="evidence about X", tier=MemoryTier.LONG)
    s.retrieve_memory(step_id="s", agent_id="a", role="researcher", query="evidence")
    s.finish_run("ok")
    summary = summarize(s.to_batch())
    assert summary.memories_retrieved >= 1


def test_expire_surfaces_without_deleting() -> None:
    s = Supervisor(_task(), memory=True)
    s.start_run()
    rec = s.remember(
        step_id="s", agent_id="a", content="short-lived", ttl_seconds=0
    )
    due = s.expire_memory()
    assert rec.id in {r.id for r in due}
    expired_events = _events(s, EventType.MEMORY_EXPIRED)
    assert len(expired_events) == 1
    # not auto-deleted
    assert s._memory_backend.get(rec.id) is not None


def test_forget_removes_and_audits() -> None:
    s = Supervisor(_task(), memory=True)
    s.start_run()
    rec = s.remember(step_id="s", agent_id="a", content="to forget")
    s.forget_memory(rec.id)
    assert s._memory_backend.get(rec.id) is None
    assert any(
        e.attributes.get("reason") == "explicit_removal"
        for e in _events(s, EventType.MEMORY_EXPIRED)
    )
