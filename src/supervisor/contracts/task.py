from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskConstraints(BaseModel):
    max_cost_usd: float | None = None
    max_latency_seconds: float | None = None
    allowed_models: list[str] = Field(default_factory=list)
    data_residency: str | None = None


class TaskContract(BaseModel):
    """Explicit contract describing what a supervised run must achieve."""

    schema_version: str = Field(default="0.1.0")
    task_id: str
    task: str
    required_outcome: list[str] = Field(default_factory=list)
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)
    quality_checks: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> TaskContract:
        return cls.model_validate(data)
