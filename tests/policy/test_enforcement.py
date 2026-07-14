import pytest

from supervisor.policy import (
    BlockedByPolicy,
    Enforcer,
    GuardDecision,
    InterventionError,
    PauseForApproval,
    StopRun,
)
from supervisor.policy.engine import DEFAULT_ENFORCE_POLICIES, DEFAULT_OBSERVE_POLICIES


def test_enforcer_allows_when_not_enforcing() -> None:
    enforcer = Enforcer(DEFAULT_ENFORCE_POLICIES, enforce=False)
    decision = enforcer.decide("duplicate_tool_protection", "dup")
    assert decision.allow is True
    assert decision.action == "observe"


def test_enforcer_blocks_when_enforcing() -> None:
    enforcer = Enforcer(DEFAULT_ENFORCE_POLICIES, enforce=True)
    decision = enforcer.decide("duplicate_tool_protection", "dup")
    assert decision.allow is False
    assert decision.action == "block"
    assert decision.mode == "enforce"


def test_enforcer_ignores_unknown_policy() -> None:
    enforcer = Enforcer(DEFAULT_ENFORCE_POLICIES, enforce=True)
    decision = enforcer.decide("does_not_exist", "x")
    assert decision.allow is True


def test_enforcer_observe_policy_not_enforced() -> None:
    # Observe-only policies never produce a blocking decision.
    enforcer = Enforcer(DEFAULT_OBSERVE_POLICIES, enforce=True)
    decision = enforcer.decide("duplicate_tool_protection", "dup")
    assert decision.allow is True
    assert decision.action == "observe"


def test_stop_raises_stop_run() -> None:
    decision = GuardDecision(
        allow=False, action="stop", policy_id="cost_budget", reason="over"
    )
    with pytest.raises(StopRun) as exc:
        raise StopRun(decision)
    assert isinstance(exc.value, InterventionError)
    assert exc.value.decision is decision


def test_pause_raises_pause_for_approval() -> None:
    decision = GuardDecision(
        allow=False,
        action="pause",
        policy_id="loop_protection",
        reason="loop",
        human_review_required=True,
    )
    with pytest.raises(PauseForApproval):
        raise PauseForApproval(decision)


def test_block_exception_is_intervention_error() -> None:
    decision = GuardDecision(
        allow=False, action="block", policy_id="duplicate_tool_protection", reason="d"
    )
    assert isinstance(BlockedByPolicy(decision), InterventionError)
