"""Versioned contracts for the request-before-execution preflight boundary."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from supervisor.context import ContextManifest
from supervisor.contracts.plan import ExecutionPlan, PlanTier, TierEstimate
from supervisor.contracts.task import TaskContract


class ApprovalStatus(StrEnum):
    ADVISORY = "advisory"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContextSource(BaseModel):
    """A caller-provided, labelled slice of master context."""

    source_id: str
    content: str
    origin: str = "caller"
    sensitivity: str = "internal"


class PreflightRequest(BaseModel):
    """Input supplied before an agent is allowed to execute."""

    schema_version: str = Field(default="0.1.0")
    task_contract: TaskContract
    master_context: list[ContextSource] = Field(default_factory=list)
    allowed_models: list[str] = Field(default_factory=list)


class RouteRecommendation(BaseModel):
    step_id: str
    role: str
    capability: str
    model: str
    tier: PlanTier
    provider: str | None = None
    reason: str


class DecisionRecord(BaseModel):
    decision_id: str
    category: str
    subject_id: str
    reason: str
    provenance: list[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    proposal_id: str
    status: ApprovalStatus
    reason: str = ""


class PreflightProposal(BaseModel):
    """Explainable, advisory plan produced before execution."""

    schema_version: str = Field(default="0.1.0")
    proposal_id: str
    task_contract: TaskContract
    execution_plan: ExecutionPlan
    cost_options: list[TierEstimate]
    context_manifests: list[ContextManifest]
    route_recommendations: list[RouteRecommendation]
    decision_ledger: list[DecisionRecord]
    status: ApprovalStatus = ApprovalStatus.ADVISORY
