"""Phase 3 planning: cost tiers and execution plans."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from supervisor.contracts.plan import ExecutionPlan, PlanStep, PlanTier, TierEstimate
from supervisor.contracts.task import RiskLevel, TaskContract

TIER_ORDER: list[PlanTier] = [
    PlanTier.MINIMUM,
    PlanTier.BALANCED,
    PlanTier.HIGH_QUALITY,
    PlanTier.MAXIMUM_ASSURANCE,
]

TIER_COST_MULTIPLIER = {
    PlanTier.MINIMUM: 0.5,
    PlanTier.BALANCED: 1.0,
    PlanTier.HIGH_QUALITY: 1.8,
    PlanTier.MAXIMUM_ASSURANCE: 3.0,
}

TIER_LATENCY_MULTIPLIER = {
    PlanTier.MINIMUM: 1.4,
    PlanTier.BALANCED: 1.0,
    PlanTier.HIGH_QUALITY: 0.7,
    PlanTier.MAXIMUM_ASSURANCE: 0.45,
}

DEFAULT_STEPS: list[dict[str, Any]] = [
    {
        "step_id": "research",
        "role": "researcher",
        "description": "Collect competitor candidates",
        "capability_requirements": ["research"],
    },
    {
        "step_id": "analysis",
        "role": "analyst",
        "description": "Verify evidence coverage and open questions",
        "capability_requirements": ["analysis"],
    },
    {
        "step_id": "synthesis",
        "role": "writer",
        "description": "Draft cited competitor brief",
        "capability_requirements": ["synthesis"],
    },
]


def _bump(tier: PlanTier, steps: int) -> PlanTier:
    idx = TIER_ORDER.index(tier)
    return TIER_ORDER[min(len(TIER_ORDER) - 1, idx + steps)]


def select_tier(task: TaskContract) -> PlanTier:
    """Deterministically choose a cost/latency tier from the task contract."""
    risk = task.risk_level
    max_cost = task.constraints.max_cost_usd
    max_latency = task.constraints.max_latency_seconds

    if risk == RiskLevel.HIGH:
        tier: PlanTier = PlanTier.HIGH_QUALITY
    elif risk == RiskLevel.MEDIUM:
        tier = PlanTier.BALANCED
    else:
        tier = PlanTier.MINIMUM

    if max_cost is not None and max_cost >= 1.0:
        tier = _bump(tier, 1)
    if max_latency is not None and max_latency <= 60:
        tier = _bump(tier, 1)
    return tier


def estimate(tier: PlanTier, task: TaskContract) -> TierEstimate:
    complexity = 1 + len(task.quality_checks)
    base_cost = 0.01 * complexity
    base_latency = 10.0 * complexity
    base_tokens = 400 * complexity
    cost_mult = TIER_COST_MULTIPLIER[tier]
    lat_mult = TIER_LATENCY_MULTIPLIER[tier]
    return TierEstimate(
        tier=tier,
        estimated_cost_usd_min=round(base_cost * cost_mult, 4),
        estimated_cost_usd_max=round(base_cost * cost_mult * 1.3, 4),
        estimated_latency_seconds_min=round(base_latency * lat_mult, 2),
        estimated_latency_seconds_max=round(base_latency * lat_mult * 1.3, 2),
        estimated_tokens_min=int(base_tokens * cost_mult),
        estimated_tokens_max=int(base_tokens * cost_mult * 1.3),
        expected_quality_coverage=(
            "Baseline coverage"
            if tier in (PlanTier.MINIMUM, PlanTier.BALANCED)
            else "High coverage with review"
        ),
        explanation=f"Tier {tier.value} chosen for task risk={task.risk_level.value}.",
    )


class Planner:
    """Builds an execution plan (tier options + steps) from a task contract."""

    def __init__(self, steps: list[dict[str, Any]] | None = None) -> None:
        self._steps = steps if steps is not None else DEFAULT_STEPS

    def build_plan(self, task: TaskContract) -> ExecutionPlan:
        chosen = select_tier(task)
        tier_options = [estimate(t, task) for t in PlanTier]
        for opt in tier_options:
            opt.recommended = opt.tier == chosen
        plan_steps = [
            PlanStep(
                step_id=s["step_id"],
                role=s["role"],
                description=s["description"],
                capability_requirements=list(s.get("capability_requirements", [])),
            )
            for s in self._steps
        ]
        return ExecutionPlan(
            plan_id=str(uuid4()),
            task_id=task.task_id,
            selected_tier=chosen,
            tier_options=tier_options,
            steps=plan_steps,
            metadata={"planner": "supervisor.planning"},
        )
