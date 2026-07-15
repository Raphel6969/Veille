from __future__ import annotations

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
