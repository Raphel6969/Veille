"""Phase 2 budget and counter tracking.

Budgets are tracked per run. The default backend is in-memory; a Redis backend
can be supplied behind ``CounterBackend`` for cross-process enforcement (Phase 2+).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CounterBackend(Protocol):
    """Minimal counter interface used by ``BudgetTracker``."""

    def inc(self, key: str, amount: int = 1) -> int: ...
    def get(self, key: str) -> int: ...
    def add_cost(self, amount: float) -> float: ...
    def cost_total(self) -> float: ...


class InMemoryCounterBackend:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._cost: float = 0.0

    def inc(self, key: str, amount: int = 1) -> int:
        self._counts[key] = self._counts.get(key, 0) + amount
        return self._counts[key]

    def get(self, key: str) -> int:
        return self._counts.get(key, 0)

    def add_cost(self, amount: float) -> float:
        self._cost += amount
        return self._cost

    def cost_total(self) -> float:
        return self._cost


class BudgetTracker:
    """Tracks cost and per-tool retry counts for a single run."""

    def __init__(
        self,
        *,
        cost_limit: float | None = None,
        retry_limit: int = 5,
        backend: CounterBackend | None = None,
    ) -> None:
        self.cost_limit = cost_limit
        self.retry_limit = retry_limit
        self._backend = backend or InMemoryCounterBackend()

    def add_cost(self, amount: float | None) -> None:
        if amount:
            self._backend.add_cost(amount)

    def cost_total(self) -> float:
        return self._backend.cost_total()

    def record_retry(self, tool_name: str) -> int:
        return self._backend.inc(f"retry:{tool_name}")

    def retry_count(self, tool_name: str) -> int:
        return self._backend.get(f"retry:{tool_name}")

    def retries_exhausted(self, tool_name: str) -> bool:
        return self._backend.get(f"retry:{tool_name}") > self.retry_limit

    def cost_exceeded(self) -> bool:
        if self.cost_limit is None:
            return False
        return self._backend.cost_total() > self.cost_limit
