from supervisor.contracts.plan import ExecutionPlan, PlanStep, PlanTier, TierEstimate
from supervisor.contracts.policy import PolicyAction, PolicyDefinition, PolicyMode
from supervisor.contracts.validation import CheckResult, ValidationReport


def test_execution_plan_skeleton() -> None:
    plan = ExecutionPlan(
        plan_id="p1",
        task_id="t1",
        selected_tier=PlanTier.BALANCED,
        steps=[PlanStep(step_id="s1", role="researcher", description="research")],
        tier_options=[
            TierEstimate(
                tier=PlanTier.BALANCED,
                estimated_cost_usd_min=0.3,
                estimated_cost_usd_max=0.7,
                estimated_latency_seconds_min=30,
                estimated_latency_seconds_max=75,
                estimated_tokens_min=4000,
                estimated_tokens_max=7000,
                expected_quality_coverage="high",
                explanation="Recommended tier",
                recommended=True,
            )
        ],
    )
    assert plan.schema_version == "0.1.0"
    assert plan.steps[0].role == "researcher"


def test_policy_definition_defaults() -> None:
    policy = PolicyDefinition(
        policy_id="dup",
        name="duplicate_search_protection",
        condition="same_tool_and_normalized_input_seen_twice",
        reason_template="Duplicate detected.",
    )
    assert policy.mode == PolicyMode.OBSERVE
    assert policy.action == PolicyAction.WARN


def test_validation_report() -> None:
    report = ValidationReport(
        run_id="r1",
        task_id="t1",
        task_contract_met=False,
        checks=[CheckResult(check_id="c1", passed=False, message="fail")],
        confidence=0.4,
        unresolved_issues=["citations_valid"],
    )
    assert not report.task_contract_met
