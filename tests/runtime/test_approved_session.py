from __future__ import annotations

import pytest

from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.contracts.events import EventType
from supervisor.contracts.preflight import (
    ApprovalDecision,
    ApprovalStatus,
    ContextSource,
    PreflightRequest,
)
from supervisor.contracts.task import TaskContract
from supervisor.sdk import Supervisor


def test_approved_session_applies_context_and_route_with_audit() -> None:
    task = TaskContract(task_id="t", task="research", quality_checks=["citations_valid"])
    supervisor = Supervisor(task)
    proposal = supervisor.preflight(
        PreflightRequest(
            task_contract=task,
            master_context=[ContextSource(source_id="q", content="Research question: competitors")],
        )
    )
    session = supervisor.approve_preflight(
        proposal, ApprovalDecision(proposal_id=proposal.proposal_id, status=ApprovalStatus.APPROVED)
    )

    session.start_run()
    assert session.context_for("research")
    assert session.route_for("research", "research").model == "mock-research"
    assert [e.event_type for e in supervisor.collector.events()] == [
        EventType.RUN_STARTED,
        EventType.PREFLIGHT_APPROVED,
        EventType.CONTEXT_ATTACHED,
        EventType.ROUTE_APPLIED,
    ]


def test_rejected_proposal_cannot_start_an_execution_session() -> None:
    task = TaskContract(task_id="t", task="research")
    supervisor = Supervisor(task)
    proposal = supervisor.preflight(PreflightRequest(task_contract=task))

    with pytest.raises(ValueError, match="approved preflight decision"):
        supervisor.approve_preflight(
            proposal,
            ApprovalDecision(proposal_id=proposal.proposal_id, status=ApprovalStatus.REJECTED),
        )


def test_advisory_preflight_preserves_normal_model_execution() -> None:
    task = TaskContract(task_id="t", task="research")
    plain = Supervisor(task)
    advised = Supervisor(task)
    request = PreflightRequest(task_contract=task)

    advised.preflight(request)
    plain_result = plain.model(
        step_id="research",
        agent_id="agent",
        model="mock-research",
        prompt="research",
        adapter=LiteLLMMockAdapter(),
    )
    advised_result = advised.model(
        step_id="research",
        agent_id="agent",
        model="mock-research",
        prompt="research",
        adapter=LiteLLMMockAdapter(),
    )

    assert advised_result == plain_result
    assert all(
        event.event_type != EventType.PREFLIGHT_APPROVED for event in advised.collector.events()
    )
