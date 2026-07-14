from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.analytics.run_summary import summarize
from supervisor.contracts.events import EventType
from supervisor.contracts.task import RiskLevel, TaskContract
from supervisor.sdk import Supervisor


def _task(risk: RiskLevel = RiskLevel.MEDIUM) -> TaskContract:
    return TaskContract(
        task_id="t",
        task="demo",
        risk_level=risk,
        quality_checks=["citations_valid"],
    )


def _events(s: Supervisor, et: EventType):
    return [e for e in s.collector.events() if e.event_type == et]


MASTER: list[str] = [
    "Research question: define the competitor landscape.",
    "Source list: verified competitor pages with citations.",
]


def test_plan_sets_selected_tier_and_start_run_carries_tier() -> None:
    s = Supervisor(_task())
    plan = s.plan()
    assert plan.selected_tier is not None
    s.start_run()
    started = _events(s, EventType.RUN_STARTED)[0]
    assert started.attributes["tier"] == plan.selected_tier.value


def test_route_model_returns_tier_aware_decision() -> None:
    s = Supervisor(_task())
    plan = s.plan()
    dec = s.route_model(step_id="research", agent_id="researcher", capability="research")
    assert dec.tier == plan.selected_tier
    assert dec.model


def test_model_with_routing_attaches_tier_attribute() -> None:
    s = Supervisor(_task())
    s.plan()
    dec = s.route_model(step_id="research", agent_id="researcher", capability="research")
    s.model(
        step_id="research",
        agent_id="researcher",
        model=dec.model,
        prompt="plan evidence collection",
        adapter=LiteLLMMockAdapter(use_mock=True),
        routing=dec,
    )
    req = _events(s, EventType.MODEL_REQUESTED)[0]
    assert req.attributes["routing_tier"] == dec.tier.value
    assert req.model_name == dec.model


def test_context_with_master_context_uses_engine() -> None:
    s = Supervisor(_task())
    s.context(
        step_id="research",
        agent_id="researcher",
        role="researcher",
        master_context=MASTER,
    )
    ctx = _events(s, EventType.CONTEXT_ATTACHED)[0]
    assert ctx.attributes["estimated_tokens"] > 0
    assert len(ctx.attributes["included"]) > 0


def test_summary_records_plan_tier_and_routing() -> None:
    s = Supervisor(_task())
    plan = s.plan()
    s.start_run()
    dec = s.route_model(step_id="research", agent_id="researcher", capability="research")
    s.model(
        step_id="research",
        agent_id="researcher",
        model=dec.model,
        prompt="plan evidence collection",
        adapter=LiteLLMMockAdapter(use_mock=True),
        routing=dec,
    )
    s.finish_run("ok")
    summary = summarize(s.to_batch())
    assert summary.plan_tier == plan.selected_tier.value
    assert len(summary.routing) == 1
