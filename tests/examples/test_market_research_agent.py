from examples.cited_market_research.agent import run_scenario


def test_success_scenario_completes() -> None:
    result = run_scenario("success")
    assert result["validation"].task_contract_met
    assert result["brief"]["competitors_count"] >= 8
    assert result["brief"]["citations_valid"] is True


def test_expensive_scenario_has_waste_patterns() -> None:
    result = run_scenario("expensive")
    assert result["validation"].task_contract_met
    batch = result["batch"]
    assert batch.metadata.get("scenario") == "expensive"
    assert batch.metadata.get("duplicate_search_count", 0) >= 1


def test_failed_validation_scenario() -> None:
    result = run_scenario("failed_validation")
    assert not result["validation"].task_contract_met
    assert result["brief"]["citations_valid"] is False
