from supervisor.policy.budgets import BudgetTracker, InMemoryCounterBackend


def test_cost_tracking_and_limit() -> None:
    tracker = BudgetTracker(cost_limit=1.0)
    tracker.add_cost(0.4)
    tracker.add_cost(0.4)
    assert tracker.cost_total() == 0.8
    assert not tracker.cost_exceeded()
    tracker.add_cost(0.3)
    assert tracker.cost_exceeded()


def test_retry_budget_exhaustion() -> None:
    tracker = BudgetTracker(retry_limit=2)
    assert tracker.record_retry("fetch") == 1
    assert tracker.record_retry("fetch") == 2
    assert not tracker.retries_exhausted("fetch")
    tracker.record_retry("fetch")
    assert tracker.retries_exhausted("fetch")


def test_per_tool_retry_isolation() -> None:
    tracker = BudgetTracker(retry_limit=1)
    tracker.record_retry("a")
    assert not tracker.retries_exhausted("b")


def test_custom_backend_used() -> None:
    backend = InMemoryCounterBackend()
    tracker = BudgetTracker(backend=backend)
    tracker.add_cost(0.5)
    assert backend.cost_total() == 0.5
