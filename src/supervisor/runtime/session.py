"""Approved execution session: the explicit bridge from proposal to a run."""

from __future__ import annotations

from typing import Any

from supervisor.contracts.events import EventType
from supervisor.contracts.preflight import ApprovalDecision, ApprovalStatus, PreflightProposal
from supervisor.routing import RoutingDecision


class ApprovedRunSession:
    def __init__(
        self, supervisor: Any, proposal: PreflightProposal, decision: ApprovalDecision
    ) -> None:
        if decision.status != ApprovalStatus.APPROVED:
            raise ValueError("an approved preflight decision is required")
        if decision.proposal_id != proposal.proposal_id:
            raise ValueError("approval decision does not match the preflight proposal")
        if proposal.task_contract.task_id != supervisor.task_id:
            raise ValueError("preflight proposal does not match this Supervisor task")
        self.supervisor = supervisor
        self.proposal = proposal
        self.decision = decision

    def start_run(self) -> None:
        self.supervisor.start_run()
        self.supervisor.collector.emit(
            EventType.PREFLIGHT_APPROVED,
            attributes={"proposal_id": self.proposal.proposal_id, "reason": self.decision.reason},
        )

    def context_for(self, step_id: str) -> list[str]:
        manifest = next((m for m in self.proposal.context_manifests if m.step_id == step_id), None)
        if manifest is None:
            raise KeyError(f"no preflight context manifest for step '{step_id}'")
        self.supervisor.context(
            step_id=manifest.step_id,
            agent_id=manifest.role,
            role=manifest.role,
            included=manifest.included,
            excluded=manifest.excluded,
            compressed=manifest.compressed,
            estimated_tokens=manifest.estimated_tokens,
            reason=f"approved preflight: {manifest.reason}",
        )
        return list(manifest.included)

    def route_for(self, step_id: str, capability: str) -> RoutingDecision:
        route = next(
            (
                r
                for r in self.proposal.route_recommendations
                if r.step_id == step_id and r.capability == capability
            ),
            None,
        )
        if route is None:
            raise KeyError(f"no preflight route for step '{step_id}' capability '{capability}'")
        self.supervisor.collector.emit(
            EventType.ROUTE_APPLIED,
            step_id=step_id,
            agent_id=route.role,
            model_name=route.model,
            attributes={"proposal_id": self.proposal.proposal_id, "reason": route.reason},
        )
        return RoutingDecision(
            capability=route.capability,
            model=route.model,
            tier=route.tier,
            provider=route.provider,
            reason=route.reason,
        )
