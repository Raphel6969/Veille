# ADR-009: Model routing by capability and tier

- **Status:** Accepted (Phase 3)
- **Date:** 2026-07-14

## Context

Phase 3 needs to choose a model per step based on what the step does
(capability) and how much assurance the run requires (tier). The supervisor
should not hard-code model names at every call site; instead, a registry of
candidate models keyed by capability plus a deterministic selector should
resolve the best fit. This keeps the demo readable and lets operators swap
models via configuration without touching code.

## Decision

- Introduce `ModelCandidate` (name, capabilities, tiers) and `ModelRegistry` in
  `routing/router.py`. The registry is seeded with mock candidates
  (`mock-research`, `mock-analysis`, `mock-synthesis`, `mock-review`) so the
  default pipeline runs without external providers.
- `ModelRouter.select(capability, tier, allowed_models=None)` returns a
  `RoutingDecision` (capability, model, tier, reason):
  - filter candidates by `capability`;
  - prefer candidates whose `tiers` include the requested tier (tier-exact),
    else fall back to the capability-matched pool;
  - if `allowed_models` is provided, intersect with it (falling back to the
    pool when the intersection is empty);
  - selection is deterministic (first match) so runs are reproducible.
- `Supervisor.route_model(step_id, agent_id, capability, allowed_models=None)`
  wraps the router, using the run's planned tier (or BALANCED when no plan
  exists). The returned `RoutingDecision` is passed to `Supervisor.model(...,
  routing=)`, which records `routing_tier` / `routing_reason` /
  `routing_capability` on the `MODEL_REQUESTED` event.
- `RunSummary.routing` is derived from `MODEL_REQUESTED` events that carry a
  `routing_tier`, so each routed model call is visible in the run report.
- Routing is advisory. It is enabled with `SUPERVISOR_PLAN=1` and only annotates
  events; it does not block or rewrite calls.

## Consequences

- Model wiring is centralized; the demo calls `route_model` + `model(routing=)`
  instead of embedding model names.
- Empty registries degrade safely to a static `mock-research` default rather
  than raising.
- Routing decisions are observable and summarizable per run.
