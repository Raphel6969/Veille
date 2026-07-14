from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    AGENT_STARTED = "agent.started"
    AGENT_FINISHED = "agent.finished"
    MODEL_REQUESTED = "model.requested"
    MODEL_COMPLETED = "model.completed"
    TOOL_REQUESTED = "tool.requested"
    TOOL_COMPLETED = "tool.completed"
    CONTEXT_ATTACHED = "context.attached"
    MEMORY_RETRIEVED = "memory.retrieved"
    RETRY_SCHEDULED = "retry.scheduled"
    RETRY_COMPLETED = "retry.completed"
    POLICY_TRIGGERED = "policy.triggered"
    INTERVENTION_APPLIED = "intervention.applied"
    VALIDATION_COMPLETED = "validation.completed"


class RunEvent(BaseModel):
    """Normalized, replayable run fact. OTel-aligned attribute names in payload."""

    schema_version: str = Field(default="0.1.0")
    event_id: str
    run_id: str
    event_type: EventType
    timestamp: datetime
    step_id: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None
    model_name: str | None = None
    duration_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    status: str | None = None
    error_message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    def normalized_input_hash(self) -> str | None:
        return self.attributes.get("normalized_input_hash")


class RunEventBatch(BaseModel):
    """Collection of events for a single run, used for replay and fixtures."""

    schema_version: str = Field(default="0.1.0")
    run_id: str
    task_id: str
    events: list[RunEvent]
    metadata: dict[str, Any] = Field(default_factory=dict)
