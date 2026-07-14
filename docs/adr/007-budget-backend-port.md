# ADR-007: Budget and counter backend port

- **Status:** Accepted (Phase 2)
- **Date:** 2026-07-14

## Context

Enforcement needs per-run counters (cost, retries) and, at scale, cross-process
budgets. Phase 2 needs a working tracker now, but the project roadmap defers
Redis (Phase 2+) and durable stores. We need a seam so the backend can change
without touching policy logic.

## Decision

Define a `CounterBackend` protocol with `inc`, `get`, `add_cost`, `cost_total`.
Ship `InMemoryCounterBackend` as the default (no infrastructure required for
tests/demo). `BudgetTracker` wraps a backend and enforces `cost_limit` /
`retry_limit`. A Redis-backed implementation can be supplied later behind the same
port with no change to `Enforcer` or `Supervisor`.

## Consequences

- Phase 2 enforcement works with zero external dependencies.
- Cross-process budgets (Redis) are a drop-in backend, not a refactor.
- `BudgetTracker` keeps the policy layer free of storage concerns.
