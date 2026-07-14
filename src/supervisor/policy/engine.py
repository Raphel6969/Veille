"""Observe-only policy engine (Phase 1).

Policies detect waste/drift and emit ``policy.triggered`` + ``intervention.applied``
events, but **never** change execution. Enforcement (warn/block/pause/stop) is
implemented in Phase 2 and is feature-flagged off here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch
from supervisor.contracts.policy import PolicyAction, PolicyDefinition, PolicyMode

RETRY_BUDGET = 5


@dataclass
class PolicyTrigger:
    policy_id: str
    reason: str
    mode: str = "observe"
    action: str = "observe"
    step_id: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None


DEFAULT_OBSERVE_POLICIES: list[PolicyDefinition] = [
    PolicyDefinition(
        policy_id="duplicate_tool_protection",
        name="Duplicate tool-call protection",
        condition="same_tool_and_normalized_input_seen_twice",
        mode=PolicyMode.OBSERVE,
        action=PolicyAction.WARN,
        reason_template="Equivalent tool request already occurred in this run.",
    ),
    PolicyDefinition(
        policy_id="retry_budget",
        name="Retry budget",
        condition="retry_count_exceeds_budget",
        mode=PolicyMode.OBSERVE,
        action=PolicyAction.WARN,
        reason_template="Retry count exceeds the configured budget.",
    ),
]


def _policy_events(
    batch: RunEventBatch,
    policy: PolicyDefinition,
    trigger: PolicyTrigger,
) -> list[RunEvent]:
    base_ts = batch.events[-1].timestamp if batch.events else None
    ts = (base_ts + timedelta(milliseconds=1)) if base_ts is not None else None
    common: dict[str, Any] = {
        "run_id": batch.run_id,
        "timestamp": ts,
        "step_id": trigger.step_id,
        "agent_id": trigger.agent_id,
        "tool_name": trigger.tool_name,
    }
    triggered = RunEvent(
        event_id=str(uuid4()),
        event_type=EventType.POLICY_TRIGGERED,
        attributes={
            "policy_id": policy.policy_id,
            "condition": policy.condition,
            "mode": policy.mode.value,
            "reason": trigger.reason,
        },
        **common,
    )
    intervention = RunEvent(
        event_id=str(uuid4()),
        event_type=EventType.INTERVENTION_APPLIED,
        attributes={
            "policy_id": policy.policy_id,
            "action": "observe",
            "mode": policy.mode.value,
            "reason": trigger.reason,
        },
        **common,
    )
    return [triggered, intervention]


def evaluate_observe(
    batch: RunEventBatch,
    policies: list[PolicyDefinition] | None = None,
) -> tuple[list[PolicyTrigger], list[RunEvent]]:
    """Return observe-only triggers and the events to append to the run batch."""
    policies = policies if policies is not None else DEFAULT_OBSERVE_POLICIES
    by_id = {p.policy_id: p for p in policies}
    triggers: list[PolicyTrigger] = []
    extra_events: list[RunEvent] = []

    dup_policy = by_id.get("duplicate_tool_protection")
    seen_status: dict[tuple[str, str], str] = {}
    for e in batch.events:
        if e.event_type == EventType.TOOL_COMPLETED and e.tool_name:
            h = e.normalized_input_hash()
            if h is None:
                continue
            key = (e.tool_name, h)
            prior = seen_status.get(key)
            if prior == "ok":
                if dup_policy is not None:
                    trigger = PolicyTrigger(
                        policy_id=dup_policy.policy_id,
                        reason=dup_policy.reason_template,
                        step_id=e.step_id,
                        agent_id=e.agent_id,
                        tool_name=e.tool_name,
                    )
                    triggers.append(trigger)
                    extra_events.extend(_policy_events(batch, dup_policy, trigger))
            seen_status[key] = e.status or "ok"

    retry_policy = by_id.get("retry_budget")
    retry_count = sum(1 for e in batch.events if e.event_type == EventType.RETRY_SCHEDULED)
    if retry_policy is not None and retry_count > RETRY_BUDGET:
        reason = (
            f"{retry_policy.reason_template} "
            f"Observed {retry_count} retries (budget {RETRY_BUDGET})."
        )
        trigger = PolicyTrigger(
            policy_id=retry_policy.policy_id,
            reason=reason,
        )
        triggers.append(trigger)
        extra_events.extend(_policy_events(batch, retry_policy, trigger))

    return triggers, extra_events
