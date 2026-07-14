"""Phase 2 enforcement runtime.

Detection lives in ``supervisor.policy.engine``. This module turns a detected
policy match into a concrete runtime decision and, when enforcement is active,
into an action the supervisor runtime applies (skip a call, stop the run, pause
for approval).

Safety: when ``enforce`` is False the enforcer always returns ``allow``; the
runtime therefore behaves exactly as in Phase 1 (observe-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from supervisor.contracts.policy import PolicyMode


@dataclass
class GuardDecision:
    allow: bool
    action: str  # observe | warn | block | pause | retry | stop
    policy_id: str | None
    reason: str
    mode: str = "observe"
    human_review_required: bool = False
    step_id: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None


class InterventionError(Exception):
    """Raised when an enforcement action must interrupt execution."""

    def __init__(self, decision: GuardDecision) -> None:
        self.decision = decision
        super().__init__(f"[{decision.action}] {decision.policy_id}: {decision.reason}")


class StopRun(InterventionError):
    """Run must stop while preserving the full trace."""


class PauseForApproval(InterventionError):
    """Run paused; human review required before continuing."""


class BlockedByPolicy(InterventionError):
    """The specific call was blocked (e.g. deduplicated)."""


class Enforcer:
    """Decides whether a detected policy match should be acted upon."""

    def __init__(self, policies: list[Any], *, enforce: bool = False) -> None:
        self._by_id = {p.policy_id: p for p in policies}
        self.enforce = enforce

    def decide(
        self,
        policy_id: str,
        reason: str,
        *,
        step_id: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
    ) -> GuardDecision:
        policy = self._by_id.get(policy_id)
        if policy is None or not (self.enforce and policy.mode == PolicyMode.ENFORCE):
            return GuardDecision(
                allow=True,
                action="observe",
                policy_id=policy_id,
                reason=reason,
                mode="observe",
                step_id=step_id,
                agent_id=agent_id,
                tool_name=tool_name,
            )
        action = policy.action.value
        return GuardDecision(
            allow=False,
            action=action,
            policy_id=policy_id,
            reason=reason,
            mode=policy.mode.value,
            human_review_required=action in ("pause", "handoff"),
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
        )


def raise_for_action(decision: GuardDecision) -> None:
    """Raise the appropriate interruption for a blocking decision.

    ``block`` and ``warn`` are non-interrupting (the caller handles dedupe /
    logging); ``stop`` and ``pause`` interrupt execution.
    """
    if decision.allow:
        return
    if decision.action == "stop":
        raise StopRun(decision)
    if decision.action == "pause":
        raise PauseForApproval(decision)
    # block / warn: handled by the caller without raising here.
    return
