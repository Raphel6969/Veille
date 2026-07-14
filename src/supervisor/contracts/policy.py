from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PolicyMode(StrEnum):
    OBSERVE = "observe"
    WARN = "warn"
    ENFORCE = "enforce"


class PolicyAction(StrEnum):
    WARN = "warn"
    BLOCK = "block"
    PAUSE = "pause"
    RETRY = "retry"
    REROUTE = "reroute"
    HANDOFF = "handoff"
    STOP = "stop"


class PolicyDefinition(BaseModel):
    """Policy contract. Evaluation engine arrives in Phase 2."""

    schema_version: str = Field(default="0.1.0")
    policy_id: str
    name: str
    condition: str
    mode: PolicyMode = PolicyMode.OBSERVE
    action: PolicyAction = PolicyAction.WARN
    reason_template: str
    enabled: bool = True
