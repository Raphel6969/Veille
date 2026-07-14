from supervisor.contracts.plan import PlanTier
from supervisor.contracts.task import RiskLevel, TaskContract
from supervisor.planning import Planner, select_tier


def _task(risk: RiskLevel = RiskLevel.MEDIUM, max_cost: float | None = None) -> TaskContract:
    return TaskContract(
        task_id="t",
        task="demo",
        risk_level=risk,
        constraints={"max_cost_usd": max_cost},
        quality_checks=["citations_valid"],
    )


def test_select_tier_is_deterministic() -> None:
    assert select_tier(_task(RiskLevel.LOW)) == select_tier(_task(RiskLevel.LOW))
    assert select_tier(_task(RiskLevel.HIGH)) in (PlanTier.HIGH_QUALITY, PlanTier.MAXIMUM_ASSURANCE)


def test_high_risk_raises_tier() -> None:
    assert select_tier(_task(RiskLevel.LOW)).value in ("minimum", "balanced")
    assert select_tier(_task(RiskLevel.HIGH)).value in ("high_quality", "maximum_assurance")


def test_high_budget_bumps_tier() -> None:
    base = select_tier(_task(RiskLevel.LOW, max_cost=None))
    bumped = select_tier(_task(RiskLevel.LOW, max_cost=5.0))
    assert bumped.value != base.value or bumped == base


def test_build_plan_has_tier_options_and_steps() -> None:
    plan = Planner().build_plan(_task())
    assert plan.selected_tier is not None
    assert len(plan.tier_options) == len(PlanTier)
    assert sum(1 for o in plan.tier_options if o.recommended) == 1
    assert len(plan.steps) == 3
    assert all(s.capability_requirements for s in plan.steps)
