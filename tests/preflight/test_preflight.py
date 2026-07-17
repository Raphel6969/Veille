from __future__ import annotations

from supervisor.contracts import ContextSource, PreflightRequest, RiskLevel, TaskContract
from supervisor.preflight import build_preflight
from supervisor.sdk import Supervisor


def _request() -> PreflightRequest:
    task = TaskContract(
        task_id="preflight-research",
        task="Produce a cited competitor brief.",
        risk_level=RiskLevel.MEDIUM,
        quality_checks=["citations_valid", "required_fields_present"],
    )
    return PreflightRequest(
        task_contract=task,
        master_context=[
            ContextSource(source_id="question", content="Research question: competitors in AI."),
            ContextSource(source_id="sources", content="Source list: approved evidence pages."),
            ContextSource(source_id="draft", content="Draft audience: engineering leaders."),
        ],
    )


def test_preflight_is_deterministic_and_has_explanations() -> None:
    first = build_preflight(_request())
    second = build_preflight(_request())

    assert first.proposal_id == second.proposal_id
    assert first.execution_plan.plan_id == second.execution_plan.plan_id
    assert len(first.cost_options) == 4
    assert len(first.context_manifests) == len(first.execution_plan.steps)
    assert len(first.route_recommendations) == len(first.execution_plan.steps)
    assert all(record.reason for record in first.decision_ledger)


def test_preflight_round_trips_and_is_advisory() -> None:
    proposal = build_preflight(_request())

    restored = type(proposal).model_validate_json(proposal.model_dump_json())

    assert restored == proposal
    assert proposal.status == "advisory"


def test_supervisor_preflight_composes_existing_runtime_components() -> None:
    request = _request()
    supervisor = Supervisor(request.task_contract)

    proposal = supervisor.preflight(request)

    assert supervisor.plan().plan_id == proposal.execution_plan.plan_id
    assert supervisor.collector.events() == []
