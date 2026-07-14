from __future__ import annotations

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    check_id: str
    passed: bool
    message: str
    details: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Deterministic validation outcome for a supervised run."""

    schema_version: str = Field(default="0.1.0")
    run_id: str
    task_id: str
    task_contract_met: bool
    checks: list[CheckResult] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    unresolved_issues: list[str] = Field(default_factory=list)
    human_review_required: bool = False
