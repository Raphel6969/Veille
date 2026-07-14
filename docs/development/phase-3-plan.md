# Phase 3 — Planner, context, and routing: Implementation Plan

**Status:** Proposed — awaiting approval. Do not begin until the Phase 3 approval gate is approved.

**Carried over:** Phase 1 (observe) and Phase 2 (enforcement) are implemented and pushed to `pre_dev`. The runtime can now *observe* and *act*. Phase 3 makes it *plan, contextualize, and route* — the supervisor actively shapes **how** work is done (which plan/tier, what context each step sees, which model serves each step) before and during execution. Phase 2 policies (cost/retry/duplicate/loop) remain the safety net on top.

## Goal

Before and during a run, the Supervisor:
1. **Plans** — selects a cost/latency tier (Min / Balanced / High / Max) from the task contract and produces an `ExecutionPlan` with step definitions and cost/latency estimates.
2. **Contextualizes** — for each step, assembles an optimized, diversified context manifest (what is included / excluded / compressed) with token accounting.
3. **Routes** — selects the best-fit model per step from a registry, honoring `allowed_models`, tier, and capability requirements, recording the decision and reason.

All three are **observe-and-act-friendly**: the planner/router propose; Phase 2 policies still enforce budgets; nothing changes the business outcome unless explicitly enabled (plan/routing are advisory by default, becoming binding when the run opts in).

## Non-goals (explicitly excluded)

- No learned/semantic routing (Phase 4+).
- No real context compression algorithms — Phase 3 ships a deterministic manifest builder (token accounting + role-based include/exclude/compress), real compression is later.
- No UI; CLI/OTel remain the surface.
- No live provider calls (mock models default).

## User-visible outcome

Running the demo (or any wrapped agent) with planning/routing enabled yields:

1. An **`ExecutionPlan`** recording the selected tier and per-step estimates.
2. Per-step **context manifests** (included / excluded / compressed + estimated tokens) emitted as `context.attached`.
3. Per-step **routing decisions** (chosen model + reason + tier) emitted alongside `model.requested`.
4. Cost/latency **estimates vs. actuals** in the run summary (`RunSummary` extended).
5. Safe default: without opt-in, behavior matches Phase 2 (planner/router still record proposals but the demo may ignore them).

## Architecture and design decisions

### D1. Planning — `src/supervisor/planning/`

- `CostTier` enum: `MIN`, `BALANCED`, `HIGH`, `MAX`.
- `Planner.select_tier(task_contract) -> CostTier`: derives tier from `constraints.max_cost_usd`, `max_latency_seconds`, and `risk_level` (e.g., high risk or tight budget → `BALANCED`/`HIGH`; loose → `MIN`/`BALANCED`). Deterministic and unit-tested.
- `ExecutionPlan` (extends the Phase 0 skeleton in `contracts/plan.py`): `plan_id`, `task_id`, `selected_tier`, `steps[]` (each with `step_id`, `role`, `description`, `capability_requirements`, `estimated_cost_usd`, `estimated_latency_seconds`), `tier_options[]`.
- `Planner.build_plan(task_contract) -> ExecutionPlan`: produces the plan + tier options with estimates. Pure/deterministic; fully tested.

### D2. Context engine — `src/supervisor/context/`

- `ContextEngine.build_manifest(master_context, role, step_id) -> ContextManifest`: returns included / excluded / compressed lists + `estimated_tokens`, with a deterministic rule (role → relevant slices of master context; large/irrelevant slices compressed/excluded). Token estimate is a simple heuristic (words/0.75).
- The SDK `Supervisor.context(...)` uses `ContextEngine` when a `master_context` is supplied; falls back to the Phase 1 manual manifest otherwise. Emits `context.attached` with the engine output.

### D3. Model routing — `src/supervisor/routing/`

- `ModelRegistry`: maps capability requirements (e.g., `research`, `synthesis`, `review`) → candidate models with pricing/tier suitability. Seeded with the demo's mock models.
- `ModelRouter.select(step, tier, allowed_models) -> RoutingDecision`: chooses the best-fit model (tier narrows the candidate set; `allowed_models` filters; capability must match), returning `model`, `tier`, `reason`.
- The SDK `Supervisor.route_model(step, capability) -> str` returns the chosen model name; `Supervisor.model(...)` uses it when the caller passes `capability` instead of an explicit `model`.

### D4. Event / summary integration

- New/extended attributes: `context.attached` already carries manifest fields; add `tier`, `estimated_tokens`. `model.requested` gains `routing_tier`, `routing_reason`. 
- `RunSummary` (Phase 1) extended with `plan_tier`, per-tier estimate vs. actual deltas, and routing decisions list.
- No new event *types* are required; existing `context.attached` / `model.requested` / `run.started` carry the new attributes.

### D5. Safety & defaults

- Planning/routing are **advisory by default**: the planner still builds a plan and the router still records a decision, but the demo uses the selected model/tier only when `SUPERVISOR_PLAN=1` (parallel to `SUPERVISOR_ENFORCE`). This keeps Phase 2 non-interference guarantees intact and makes Phase 3 opt-in.
- Phase 2 policies continue to enforce on top (a routed model that blows the budget is still stopped).

## Files / components expected to change

| Path | Change |
|---|---|
| `src/supervisor/planning/` (new) | `planner.py` (tier + `ExecutionPlan`), `tiers.py` |
| `src/supervisor/context/` (new) | `engine.py` (`ContextEngine.build_manifest`) |
| `src/supervisor/routing/` (new) | `registry.py`, `router.py` (`ModelRouter.select`) |
| `src/supervisor/contracts/plan.py` | Promote `ExecutionPlan` from skeleton to implemented fields |
| `src/supervisor/sdk/supervisor.py` | `plan()`, `route_model()`, `context()` uses `ContextEngine` |
| `src/supervisor/analytics/run_summary.py` | `plan_tier`, estimate-vs-actual, routing decisions |
| `examples/cited_market_research/agent.py` | Use planner (tier) + router (per-node models) + context engine |
| `tests/planning/`, `tests/context/`, `tests/routing/`, `tests/sdk/` | New suites |
| `tests/examples/` | Scenario reflects plan/routing when enabled |

## Documentation deliverables

- **ADR-008:** Tier/cost model and `ExecutionPlan` shape.
- **ADR-009:** Model routing — registry, capability fit, tier narrowing.
- `docs/data-contracts.md`: extend `context.attached` / `model.requested` attribute registry; finalize `ExecutionPlan` schema.
- `docs/architecture.md`, `docs/runtime-chain.md`: mark *Inspect / Plan / Estimate / Optimize Context / Route Model* as implemented (advisory).
- `docs/integrations.md`: routing registry contract.
- `docs/operations.md`: document `SUPERVISOR_PLAN`, viewing plan/routing via CLI.
- `README.md`, `docs/roadmap.md`, `CHANGELOG.md`: update Phase 3 status after completion.

## Tests and acceptance criteria

- **Planner:** `select_tier` is deterministic from contract; `build_plan` returns valid `ExecutionPlan` with estimates; tier options present.
- **Context engine:** manifest include/exclude/compress is role-sensitive and deterministic; token estimate positive.
- **Router:** selects capability-matching model; respects `allowed_models` and tier; returns reason; falls back safely when no match.
- **SDK integration:** `route_model` returns a model; `context()` emits engine manifest; `run.started` carries `plan_tier`.
- **Summary:** `RunSummary` includes `plan_tier` and routing decisions; estimate-vs-actual computable.
- **Safe default:** without `SUPERVISOR_PLAN`, demo output is byte-identical to Phase 2.
- **Compose with Phase 2:** a routed run that exceeds budget is still stopped by `cost_budget`/`retry_budget`.
- **Contract:** `ExecutionPlan` / manifest round-trips; new attributes documented and tested.

**Master-prompt acceptance (Phase 3):**

- The supervisor proposes a plan/tier and per-step context + model before work. ✓
- Cost/latency are estimated up front and comparable to actuals. ✓
- Routing decision is explainable (model + reason + tier). ✓
- Safe default preserves Phase 2 non-interference. ✓
- Trace/event schema contract tests pass. ✓

## Risks, assumptions, dependencies

- **Tier heuristics are approximate** — derived from contract constraints; refined with real pricing later (ADR-003 mock pricing).
- **Context "compression" is illustrative** — deterministic slicing, not semantic; real compression Phase 4+.
- **Routing registry is seeded with mock models** — real provider registry is an integration (LiteLLM) added when paid mode is enabled.
- **Advisory vs binding:** default advisory to protect existing behavior; binding opt-in via `SUPERVISOR_PLAN`.
- **Compose with enforcement:** planner/router never bypass Phase 2 policies.

---

## Phase 3 approval gate

```
Phase 3 is ready to begin.

Goal: Make the supervisor plan, contextualize, and route each run.

Scope:
  - Planning: cost tiers (Min/Balanced/High/Max) + ExecutionPlan with estimates
  - Context engine: per-step manifest (included/excluded/compressed) + tokens
  - Model routing: capability + tier fit from a registry, with reasons
  - SDK: plan(), route_model(), context() uses ContextEngine
  - RunSummary: plan_tier, estimate-vs-actual, routing decisions
  - Demo: planner picks tier; router assigns models per node; context engine manifests

Not in scope:
  - semantic / learned routing (Phase 4+)
  - real context compression algorithms
  - Next.js control-plane UI

Key decisions / assumptions:
  - planning/routing advisory by default (SUPERVISOR_PLAN opt-in)
  - deterministic tier heuristics from contract constraints
  - registry seeded with mock models; real LiteLLM registry later
  - Phase 2 policies still enforce on top

Validation:
  - pytest: planner, context engine, router, SDK integration, summary,
    safe-default regression, compose-with-enforcement
  - ruff + mypy clean
  - demo runs without API keys on Python 3.14

Risks / questions:
  - tier heuristic accuracy (approximate; refined with real pricing)
  - context compression illustrative until Phase 4
  - routing registry seeded with mocks

May I implement Phase 3 now?
```
