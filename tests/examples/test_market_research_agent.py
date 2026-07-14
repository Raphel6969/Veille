import os

from examples.cited_market_research.agent import run_scenario

from supervisor.contracts.events import EventType
from supervisor.sdk import supervisor as sdk_supervisor


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


def test_optimize_active_serves_duplicate_from_cache() -> None:
    os.environ["SUPERVISOR_OPTIMIZE"] = "1"
    os.environ["SUPERVISOR_OPTIMIZE_MODE"] = "active"
    os.environ["SUPERVISOR_CACHE_APPROVED"] = "1"
    real_emit = sdk_supervisor.RunCollector.emit
    counts: dict[str, int] = {}

    def counting(self: object, et: EventType, **kw: object):
        counts[et.value] = counts.get(et.value, 0) + 1
        return real_emit(self, et, **kw)

    try:
        sdk_supervisor.RunCollector.emit = counting  # type: ignore[assignment]
        try:
            result = run_scenario("expensive")
        finally:
            sdk_supervisor.RunCollector.emit = real_emit  # type: ignore[assignment]
    finally:
        os.environ.pop("SUPERVISOR_OPTIMIZE", None)
        os.environ.pop("SUPERVISOR_OPTIMIZE_MODE", None)
        os.environ.pop("SUPERVISOR_CACHE_APPROVED", None)

    assert counts.get("optimization.applied", 0) >= 1
    # A served duplicate avoids the duplicate search cost.
    assert result["total_cost_usd"] < 0.023


def test_memory_enabled_governs_retrieval() -> None:
    os.environ["SUPERVISOR_MEMORY"] = "1"
    real_emit = sdk_supervisor.RunCollector.emit
    counts: dict[str, int] = {}

    def counting(self: object, et: EventType, **kw: object):
        counts[et.value] = counts.get(et.value, 0) + 1
        return real_emit(self, et, **kw)

    try:
        sdk_supervisor.RunCollector.emit = counting  # type: ignore[assignment]
        try:
            run_scenario("success")
        finally:
            sdk_supervisor.RunCollector.emit = real_emit  # type: ignore[assignment]
    finally:
        os.environ.pop("SUPERVISOR_MEMORY", None)

    assert counts.get("memory.retrieved", 0) >= 1


