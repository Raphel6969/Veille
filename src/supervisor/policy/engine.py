"""Policy engine (Phase 1 observe-only + Phase 2 enforcement support).

Policies detect waste/drift. In ``observe`` mode they emit ``policy.triggered``
+ ``intervention.applied`` events but never change execution. With enforcement
enabled, the recommended action (``block`` / ``stop`` / ``pause`` / ...) is
applied by the runtime (see ``supervisor.policy.enforcement``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch
from supervisor.contracts.policy import PolicyAction, PolicyDefinition, PolicyMode

RETRY_BUDGET = 5
LOOP_LIMIT = 3


@dataclass
class PolicyTrigger:
    policy_id: str
    reason: str
    mode: str = "observe"
    action: str = "observe"
    step_id: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None


@dataclass
class PolicyDecision:
    """Outcome of evaluating a policy against a run.

    ``action`` is the policy's configured action when enforcement is active,
    otherwise ``observe``. ``applied`` is True only when the runtime should (and
    did) act on it.
    """

    policy_id: str
    reason: str
    action: str
    mode: str = "observe"
    applied: bool = False
    human_review_required: bool = False
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

DEFAULT_ENFORCE_POLICIES: list[PolicyDefinition] = [
    PolicyDefinition(
        policy_id="duplicate_tool_protection",
        name="Duplicate tool-call protection",
        condition="same_tool_and_normalized_input_seen_twice",
        mode=PolicyMode.ENFORCE,
        action=PolicyAction.BLOCK,
        reason_template="Equivalent successful tool call already deduplicated.",
    ),
    PolicyDefinition(
        policy_id="retry_budget",
        name="Retry budget",
        condition="retry_count_exceeds_budget",
        mode=PolicyMode.ENFORCE,
        action=PolicyAction.STOP,
        reason_template="Retry budget exceeded; run stopped.",
    ),
    PolicyDefinition(
        policy_id="cost_budget",
        name="Cost budget",
        condition="total_cost_exceeds_max",
        mode=PolicyMode.ENFORCE,
        action=PolicyAction.STOP,
        reason_template="Estimated cost exceeded the task contract budget.",
    ),
    PolicyDefinition(
        policy_id="stall_protection",
        name="Stall protection",
        condition="step_exceeds_max_latency",
        mode=PolicyMode.ENFORCE,
        action=PolicyAction.STOP,
        reason_template="A step exceeded its maximum latency; run stopped.",
    ),
    PolicyDefinition(
        policy_id="loop_protection",
        name="Loop protection",
        condition="identical_step_sequence_repeats",
        mode=PolicyMode.ENFORCE,
        action=PolicyAction.STOP,
        reason_template="Identical tool sequence repeated; possible run-away loop.",
    ),
]


def _action_for(policy: PolicyDefinition, enforce: bool) -> tuple[str, bool]:
    if enforce and policy.mode == PolicyMode.ENFORCE:
        return policy.action.value, True
    return "observe", False


def _emit_decision(
    batch: RunEventBatch,
    policy: PolicyDefinition,
    decision: PolicyDecision,
) -> list[RunEvent]:
    base_ts = batch.events[-1].timestamp if batch.events else None
    ts = (base_ts + timedelta(milliseconds=1)) if base_ts is not None else None
    common: dict[str, Any] = {
        "run_id": batch.run_id,
        "timestamp": ts,
        "step_id": decision.step_id,
        "agent_id": decision.agent_id,
        "tool_name": decision.tool_name,
    }
    triggered = RunEvent(
        event_id=str(uuid4()),
        event_type=EventType.POLICY_TRIGGERED,
        attributes={
            "policy_id": policy.policy_id,
            "condition": policy.condition,
            "mode": decision.mode,
            "reason": decision.reason,
        },
        **common,
    )
    intervention = RunEvent(
        event_id=str(uuid4()),
        event_type=EventType.INTERVENTION_APPLIED,
        attributes={
            "policy_id": policy.policy_id,
            "action": decision.action,
            "mode": decision.mode,
            "reason": decision.reason,
            "human_review_required": decision.human_review_required,
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
                    extra_events.extend(_emit_decision(batch, dup_policy, _to_decision(trigger)))
            seen_status[key] = e.status or "ok"

    retry_policy = by_id.get("retry_budget")
    retry_count = sum(1 for e in batch.events if e.event_type == EventType.RETRY_SCHEDULED)
    if retry_policy is not None and retry_count > RETRY_BUDGET:
        reason = (
            f"{retry_policy.reason_template} "
            f"Observed {retry_count} retries (budget {RETRY_BUDGET})."
        )
        trigger = PolicyTrigger(policy_id=retry_policy.policy_id, reason=reason)
        triggers.append(trigger)
        extra_events.extend(_emit_decision(batch, retry_policy, _to_decision(trigger)))

    return triggers, extra_events


def _to_decision(trigger: PolicyTrigger) -> PolicyDecision:
    return PolicyDecision(
        policy_id=trigger.policy_id,
        reason=trigger.reason,
        action="observe",
        mode=trigger.mode,
        step_id=trigger.step_id,
        agent_id=trigger.agent_id,
        tool_name=trigger.tool_name,
    )


def evaluate(
    batch: RunEventBatch,
    *,
    policies: list[PolicyDefinition] | None = None,
    enforce: bool = False,
    max_cost_usd: float | None = None,
    max_latency_seconds: float | None = None,
    loop_limit: int = LOOP_LIMIT,
) -> tuple[list[PolicyDecision], list[RunEvent]]:
    """Evaluate a completed batch against the policy set.

    In ``observe`` mode every match yields ``action="observe"`` (no runtime
    effect). With ``enforce=True``, matches against ``ENFORCE``-mode policies
    carry their configured action and ``applied=True``.
    """
    policies = policies if policies is not None else DEFAULT_ENFORCE_POLICIES
    by_id = {p.policy_id: p for p in policies}
    decisions: list[PolicyDecision] = []
    extra_events: list[RunEvent] = []

    def _decide(policy: PolicyDefinition, reason: str, **kw: Any) -> PolicyDecision | None:
        action, applied = _action_for(policy, enforce)
        if action == "observe" and not applied:
            # Still record the observation so the audit trail is complete.
            pass
        decision = PolicyDecision(
            policy_id=policy.policy_id,
            reason=reason,
            action=action,
            mode=policy.mode.value,
            applied=applied,
            human_review_required=action in ("pause", "handoff"),
            **kw,
        )
        return decision

    # Duplicate tool calls (only after a prior successful call).
    dup_policy = by_id.get("duplicate_tool_protection")
    if dup_policy is not None:
        seen_status: dict[tuple[str, str], str] = {}
        for e in batch.events:
            if e.event_type == EventType.TOOL_COMPLETED and e.tool_name:
                h = e.normalized_input_hash()
                if h is None:
                    continue
                key = (e.tool_name, h)
                prior = seen_status.get(key)
                if prior == "ok":
                    decision = _decide(
                        dup_policy,
                        dup_policy.reason_template,
                        step_id=e.step_id,
                        agent_id=e.agent_id,
                        tool_name=e.tool_name,
                    )
                    if decision is not None:
                        decisions.append(decision)
                        extra_events.extend(_emit_decision(batch, dup_policy, decision))
                seen_status[key] = e.status or "ok"

    # Retry budget.
    retry_policy = by_id.get("retry_budget")
    if retry_policy is not None:
        retry_count = sum(1 for e in batch.events if e.event_type == EventType.RETRY_SCHEDULED)
        if retry_count > RETRY_BUDGET:
            decision = _decide(
                retry_policy,
                f"{retry_policy.reason_template} "
                f"Observed {retry_count} retries (budget {RETRY_BUDGET}).",
            )
            if decision is not None:
                decisions.append(decision)
                extra_events.extend(_emit_decision(batch, retry_policy, decision))

    # Cost budget.
    cost_policy = by_id.get("cost_budget")
    if cost_policy is not None and max_cost_usd is not None:
        total = sum(e.cost_usd or 0.0 for e in batch.events)
        if total > max_cost_usd:
            decision = _decide(
                cost_policy,
                f"{cost_policy.reason_template} Observed ${total:.4f} (max ${max_cost_usd:.4f}).",
            )
            if decision is not None:
                decisions.append(decision)
                extra_events.extend(_emit_decision(batch, cost_policy, decision))

    # Stall protection.
    stall_policy = by_id.get("stall_protection")
    if stall_policy is not None and max_latency_seconds is not None:
        limit_ms = max_latency_seconds * 1000.0
        for e in batch.events:
            if (
                e.event_type == EventType.TOOL_COMPLETED
                and e.duration_ms is not None
                and e.duration_ms > limit_ms
            ):
                decision = _decide(
                    stall_policy,
                    f"{stall_policy.reason_template} Step took {e.duration_ms:.0f}ms "
                    f"(max {limit_ms:.0f}ms).",
                    step_id=e.step_id,
                    agent_id=e.agent_id,
                    tool_name=e.tool_name,
                )
                if decision is not None:
                    decisions.append(decision)
                    extra_events.extend(_emit_decision(batch, stall_policy, decision))
                break

    # Loop protection (repeated identical tool calls).
    loop_policy = by_id.get("loop_protection")
    if loop_policy is not None:
        counts: dict[tuple[str, str], int] = {}
        for e in batch.events:
            if e.event_type == EventType.TOOL_COMPLETED and e.tool_name:
                h = e.normalized_input_hash()
                if h is None:
                    continue
                key = (e.tool_name, h)
                counts[key] = counts.get(key, 0) + 1
                if counts[key] > loop_limit:
                    decision = _decide(
                        loop_policy,
                        f"{loop_policy.reason_template} Tool {e.tool_name} repeated "
                        f"{counts[key]} times.",
                        step_id=e.step_id,
                        agent_id=e.agent_id,
                        tool_name=e.tool_name,
                    )
                    if decision is not None:
                        decisions.append(decision)
                        extra_events.extend(_emit_decision(batch, loop_policy, decision))
                    break

    return decisions, extra_events
