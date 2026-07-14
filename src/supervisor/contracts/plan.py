from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PlanTier(StrEnum):
    MINIMUM = "minimum"
    BALANCED = "balanced"
    HIGH_QUALITY = "high_quality"
    MAXIMUM_ASSURANCE = "maximum_assurance"


class TierEstimate(BaseModel):
    tier: PlanTier
    estimated_cost_usd_min: float
    estimated_cost_usd_max: float
    estimated_latency_seconds_min: float
    estimated_latency_seconds_max: float
    estimated_tokens_min: int
    estimated_tokens_max: int
    expected_quality_coverage: str
    explanation: str
    recommended: bool = False


class PlanStep(BaseModel):
    step_id: str
    role: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    expected_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    capability_requirements: list[str] = Field(default_factory=list)
    assigned_model: str | None = None


class ExecutionPlan(BaseModel):
    """Skeleton execution plan. Planner logic arrives in Phase 3."""

    schema_version: str = Field(default="0.1.0")
    plan_id: str
    task_id: str
    selected_tier: PlanTier | None = None
    tier_options: list[TierEstimate] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    policy_limits: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
