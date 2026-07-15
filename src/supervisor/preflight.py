"""Compose planner, context, and router into the single advisory preflight path."""

from __future__ import annotations

import hashlib
from uuid import NAMESPACE_URL, uuid5

from supervisor.context import ContextEngine
from supervisor.contracts.preflight import (
    DecisionRecord,
    PreflightProposal,
    PreflightRequest,
    RouteRecommendation,
)
from supervisor.planning import Planner
from supervisor.routing import ModelRouter


def _stable_id(prefix: str, value: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"veille:{prefix}:{value}"))


def _request_fingerprint(request: PreflightRequest) -> str:
    payload = request.model_dump_json(exclude_none=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_preflight(
    request: PreflightRequest,
    *,
    planner: Planner | None = None,
    context_engine: ContextEngine | None = None,
    router: ModelRouter | None = None,
) -> PreflightProposal:
    """Build an explainable proposal without starting or changing a run."""
    fingerprint = _request_fingerprint(request)
    planner = planner or Planner()
    context_engine = context_engine or ContextEngine()
    router = router or ModelRouter()
    plan = planner.build_plan(request.task_contract).model_copy(
        update={"plan_id": _stable_id("plan", fingerprint)}
    )
    if plan.selected_tier is None:  # pragma: no cover - Planner always selects a tier
        raise ValueError("preflight requires an execution plan with a selected tier")
    context = [source.content for source in request.master_context]
    manifests = [
        context_engine.build_manifest(context, step.role, step.step_id) for step in plan.steps
    ]
    allowed_models = request.allowed_models or request.task_contract.constraints.allowed_models
    routes: list[RouteRecommendation] = []
    ledger: list[DecisionRecord] = [
        DecisionRecord(
            decision_id=_stable_id("task", fingerprint),
            category="task_contract",
            subject_id=request.task_contract.task_id,
            reason="Preflight evaluated the supplied task contract before execution.",
            provenance=["caller:task_contract"],
        ),
        DecisionRecord(
            decision_id=_stable_id("plan", fingerprint),
            category="execution_plan",
            subject_id=plan.plan_id,
            reason=(
                f"Selected {plan.selected_tier.value if plan.selected_tier else 'no'} tier "
                "from task risk and constraints."
            ),
            provenance=["planner:select_tier"],
        ),
    ]
    for manifest in manifests:
        ledger.append(
            DecisionRecord(
                decision_id=_stable_id("context", f"{fingerprint}:{manifest.step_id}"),
                category="context_manifest",
                subject_id=manifest.step_id,
                reason=manifest.reason,
                provenance=[source.source_id for source in request.master_context],
            )
        )
    for step in plan.steps:
        for capability in step.capability_requirements:
            decision = router.select(capability, plan.selected_tier, allowed_models or None)
            route = RouteRecommendation(
                step_id=step.step_id,
                role=step.role,
                capability=capability,
                model=decision.model,
                tier=decision.tier,
                provider=decision.provider,
                reason=decision.reason,
            )
            routes.append(route)
            ledger.append(
                DecisionRecord(
                    decision_id=_stable_id("route", f"{fingerprint}:{step.step_id}:{capability}"),
                    category="model_route",
                    subject_id=step.step_id,
                    reason=decision.reason,
                    provenance=["router:capability_tier", f"capability:{capability}"],
                )
            )
    return PreflightProposal(
        proposal_id=_stable_id("proposal", fingerprint),
        task_contract=request.task_contract,
        execution_plan=plan,
        cost_options=plan.tier_options,
        context_manifests=manifests,
        route_recommendations=routes,
        decision_ledger=ledger,
    )
