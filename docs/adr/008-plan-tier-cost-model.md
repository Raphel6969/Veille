# ADR-008: Plan tier and cost/latency model

- **Status:** Accepted (Phase 3)
- **Date:** 2026-07-14

## Context

Phase 3 makes the supervisor advisory by default and adds a planner that matches
the task risk to an assurance tier. We need a small, deterministic model that
maps a task to a tier and expresses the relative cost/latency of each tier so
downstream routing and reporting can reason about trade-offs without calling a
pricing API.

## Decision

- Represent assurance levels with `PlanTier` (MINIMUM, BALANCED, HIGH_QUALITY,
  MAXIMUM_ASSURANCE) in `contracts/plan.py`.
- `select_tier(task)` is a pure, deterministic function: it starts from a
  risk-derived baseline (LOW→MINIMUM, MEDIUM→BALANCED, HIGH→HIGH_QUALITY,
  CRITICAL→MAXIMUM_ASSURANCE), then bumps one tier when the task's
  `max_cost_usd` allows more assurance, and clamps to the top tier on
  CRITICAL. The function is unit-tested for determinism and monotonicity.
- `Planner.build_plan(task)` returns an `ExecutionPlan` with a `tier_options`
  list (one `TierEstimate` per tier, carrying a cost/latency multiplier) and a
  `steps` list derived from `DEFAULT_STEPS`. Exactly one option is flagged
  `recommended`, coinciding with `plan.selected_tier`.
- Cost/latency are expressed as **relative multipliers** (`TIER_COST_MULTIPLIER`,
  `TIER_LATENCY_MULTIPLIER`) keyed by tier, not absolute currency. This keeps the
  model provider-agnostic and testable; absolute cost is still measured
  empirically by the budget tracker at runtime.
- Tier selection is advisory. It is gated behind `SUPERVISOR_PLAN=1` (mirroring
  `SUPERVISOR_ENFORCE`) and only annotates events; it never blocks a run.

## Consequences

- Routing and reporting share one canonical tier vocabulary.
- The planner is fully unit-testable with no network or pricing dependency.
- Multipliers are intentionally coarse; fine-grained routing cost still comes
  from measured `MODEL_COMPLETED` events.
