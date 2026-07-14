from supervisor.analytics.run_summary import summarize
from supervisor.contracts.events import EventType
from supervisor.contracts.task import RiskLevel, TaskContract
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


def test_no_optimization_events_when_disabled() -> None:
    s = Supervisor(_task())
    s.start_run()
    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=lambda: "r")
    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=lambda: "r")
    assert not _events(s, EventType.OPTIMIZATION_RECOMMENDED)
    assert not _events(s, EventType.OPTIMIZATION_APPLIED)


def test_dry_run_recommends_but_executes() -> None:
    s = Supervisor(_task(), optimize=True, optimize_mode="dry_run")
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=fn, idempotent=True)
    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=fn, idempotent=True)

    assert calls["n"] == 2  # dry-run still executes
    reqs = _events(s, EventType.TOOL_REQUESTED)
    assert reqs[1].attributes.get("match_type") == "exact"
    assert len(_events(s, EventType.OPTIMIZATION_RECOMMENDED)) == 1
    assert not _events(s, EventType.OPTIMIZATION_APPLIED)


def test_active_serves_from_cache() -> None:
    s = Supervisor(_task(), optimize=True, optimize_mode="active")
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=fn, idempotent=True)
    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=fn, idempotent=True)

    assert calls["n"] == 1  # second served from cache
    assert len(_events(s, EventType.OPTIMIZATION_APPLIED)) == 1
    completed = _events(s, EventType.TOOL_COMPLETED)
    assert completed[1].attributes.get("cache_hit") is True


def test_non_idempotent_never_served() -> None:
    s = Supervisor(_task(), optimize=True, optimize_mode="active")
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=fn)
    s.tool(step_id="s", agent_id="a", tool_name="t", input={"x": 1}, fn=fn)
    assert calls["n"] == 2  # not idempotent -> re-executed


def test_summary_accounts_for_cache() -> None:
    s = Supervisor(_task(), optimize=True, optimize_mode="active")
    s.start_run()
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="t",
        input={"x": 1},
        fn=lambda: "r",
        idempotent=True,
        cost_usd=0.01,
    )
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="t",
        input={"x": 1},
        fn=lambda: "r",
        idempotent=True,
        cost_usd=0.01,
    )
    s.finish_run("ok")
    summary = summarize(s.to_batch())
    assert summary.cache_hits >= 1
    assert summary.cache_served >= 1
    assert summary.estimated_savings_usd > 0
