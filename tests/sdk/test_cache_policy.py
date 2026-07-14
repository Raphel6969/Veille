"""Approved cache policy rules (v0.2.0 partner-validated).

Covers the three explicit rules:
  1. Cacheable only for identical normalized inputs (exact), not semantic.
  2. Cache key includes tenant/project/tool+policy version/auth+context boundaries.
  3. Serving requires partner confirmation (gate); expired/uncertain re-execute.
"""

from __future__ import annotations

from supervisor.contracts.events import EventType
from supervisor.contracts.task import RiskLevel, TaskContract
from supervisor.optimize.policy import CachePolicy, build_cache_key
from supervisor.sdk import Supervisor


def _task() -> TaskContract:
    return TaskContract(
        task_id="t",
        task="demo",
        risk_level=RiskLevel.MEDIUM,
        quality_checks=["citations_valid"],
    )


def _events(s: Supervisor, et: EventType):
    return [e for e in s.collector.events() if e.event_type == et]


def _approved(tools=("search_competitors",)) -> CachePolicy:
    return CachePolicy(cacheable_tools=set(tools), approved_override=True)


def test_rule1_exact_normalized_input_served() -> None:
    s = Supervisor(_task(), optimize=True, optimize_mode="active", cache_policy=_approved())
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
    )
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
    )
    assert calls["n"] == 1  # identical normalized input -> served


def test_rule1_semantic_near_duplicate_not_served() -> None:
    # In dry-run a semantic near-duplicate is flagged (recommended) but never
    # served; in active mode it would also not be served. We assert the gate:
    # uncertain matches must re-execute (calls == 2, no APPLIED).
    s = Supervisor(_task(), optimize=True, optimize_mode="dry_run", cache_policy=_approved())
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi"},
        fn=fn,
        idempotent=True,
    )
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={
            "q": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"
        },  # noqa: E501
        fn=fn,
        idempotent=True,
    )
    # Near-duplicate is recommended but NEVER served (uncertain -> re-execute).
    assert calls["n"] == 2
    recs = _events(s, EventType.OPTIMIZATION_RECOMMENDED)
    assert recs and recs[0].attributes.get("match_type") == "semantic"
    assert not _events(s, EventType.OPTIMIZATION_APPLIED)


def test_rule2_boundary_change_is_a_miss() -> None:
    s = Supervisor(
        _task(),
        optimize=True,
        optimize_mode="active",
        cache_policy=_approved(),
        tenant="acme",
        project="p1",
    )
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
        auth_scope="user-A",
        context_boundary="ctx-1",
    )
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
        auth_scope="user-B",
        context_boundary="ctx-1",
    )
    assert calls["n"] == 2  # different auth scope -> distinct cache key -> miss


def test_rule2_key_contains_boundaries() -> None:
    k = build_cache_key(
        "search_competitors",
        "query",
        tenant="acme",
        project="p1",
        tool_version="v2",
        policy_version="pol3",
        auth_scope="user-A",
        context_boundary="ctx-1",
    )
    assert "tenant=acme" in k
    assert "project=p1" in k
    assert "tool_version=v2" in k
    assert "policy_version=pol3" in k
    assert "auth=user-A" in k
    assert "ctx=ctx-1" in k


def test_rule3_gate_blocks_serving_without_confirmation() -> None:
    # Not approved (no override, 0 confirmations) -> active mode still re-executes.
    pending = CachePolicy(cacheable_tools={"search_competitors"})
    assert not pending.approved
    s = Supervisor(_task(), optimize=True, optimize_mode="active", cache_policy=pending)
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
    )
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
    )
    assert calls["n"] == 2  # gate not met -> not served
    assert not _events(s, EventType.OPTIMIZATION_APPLIED)


def test_rule3_confirmation_threshold_met() -> None:
    ready = CachePolicy(cacheable_tools={"search_competitors"}, partner_confirmations=3)
    assert ready.approved
    s = Supervisor(_task(), optimize=True, optimize_mode="active", cache_policy=ready)
    s.start_run()
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "r"

    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
    )
    s.tool(
        step_id="s",
        agent_id="a",
        tool_name="search_competitors",
        input={"q": "same query"},
        fn=fn,
        idempotent=True,
    )
    assert calls["n"] == 1  # confirmed -> served
