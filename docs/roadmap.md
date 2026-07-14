# Roadmap

Phase-by-phase delivery per the [master prompt](development/AI_DEVELOPER_MASTER_PROMPT.md) and [blueprint](development/AI_RUNTIME_SUPERVISOR_BLUEPRINT.md).

| Phase | Name | Status | Exit criteria summary |
|---|---|---|---|
| 0 | Discovery, repository setup, baseline | **Complete (verified)** | Contracts, docs, synthetic workflow, fixtures, metrics defined; `pytest`/ruff/mypy green |
| 1 | Observe and explain | **Implemented (pending release)** | SDK, automatic events, timeline, observe-only policies ([plan](development/phase-1-plan.md)) |
| 2 | Deterministic protection | **Implemented (pending release)** | Budgets, duplicate/loop detection, intervention modes ([plan](development/phase-2-plan.md)) |
| 3 | Planner, context, routing | **Implemented (pending release)** | Cost tiers, context manifests, model routing, validation ([plan](development/phase-3-plan.md)) |
| 4 | Adaptive optimization | Not started | Semantic detection, caching, experiments |
| 5 | Memory and enterprise | Not started | Multi-tenancy, RBAC, audit, retention |
| 6 | Simulation and learned policies | Not started | Offline simulation, learned recommendations |

## Phase 0 deliverables

- [x] Repository structure and documentation system
- [x] Task contract and event schema v0.1
- [x] Synthetic cited market-research LangGraph workflow
- [x] Trace fixtures (success, expensive, failed_validation) — committed under `fixtures/traces/`
- [x] Adapter ports: LangGraph, LiteLLM mock, OTel interface
- [x] Baseline metrics and report template
- [x] Docker Compose, CI, dev scripts

### Phase 0 verification (2026-07-14)

- `pytest` — **23 passed** (contract round-trip, fixture load, adapter protocol, example smoke)
- `ruff check` / `ruff format` — clean
- `mypy src/supervisor` — clean (strict)
- Trace fixtures generated and committed; demo runs without API keys on Python 3.14
- Known issue found and fixed during verification: run summary `duplicate_search_count`/`retry_count` were not copied into `RunEventBatch.metadata` (now included in `examples/cited_market_research/agent.py`)

> **Baseline credibility:** Phase 0 baselines are synthetic. See `docs/evaluation.md`.

## Phase 1 deliverables

- [x] Python SDK (`Supervisor` + `RunCollector`) for zero-touch event emission
- [x] LangGraph adapter implementation (callback-based instrumentation)
- [x] Automatic event collection (model/tool/retry/context/node/validation)
- [x] Cost and waste aggregation (`summarize` / `RunSummary`)
- [x] Observe-only policy evaluation (duplicate, retry storm, cost overrun, validation)
- [x] Minimal run-explorer CLI (`explore` for fixtures and live runs)
- [x] OTel export implementation (Console + OTLP)
- [x] Demo refactored to the SDK; docs (ADR-004, ADR-005, registry, architecture)

### Phase 1 verification (2026-07-14)

- `pytest` — **39 passed** (sdk, analytics, policy, telemetry mapping, langgraph adapter, cli, demo)
- `ruff check` / `ruff format` — clean
- `mypy src/supervisor` — clean (strict)
- `python -m supervisor.cli explore --live --scenario expensive --policy` surfaces duplicate/retry/cost observations
- Works without API keys on Python 3.14

## Confirmed decisions

| Decision | Choice |
|---|---|
| First framework adapter | LangGraph |
| First workflow | Cited market-research |
| Traces | Synthetic fixtures |
| Observability | OTel interface only; vendor deferred |
| Model access | LiteLLM mock; paid opt-in |

## Explicit deferrals

- Next.js control plane UI (Phase 1 delivered CLI-first; Phase 2 enforcement observable via CLI/OTel/audit)
- PostgreSQL/Redis/MinIO deep wiring (Phase 2+; Redis counters optional behind a port)
- Real LiteLLM provider calls (opt-in)
- Langfuse/Phoenix/LangSmith export (Phase 1+; OTel export implemented)

## Phase 2 deliverables

- [x] Enforcement engine: detection (`evaluate`) separated from action (`Enforcer`)
- [x] Guard points in `Supervisor.tool()` / `Supervisor.retry()` (call-site, framework-agnostic)
- [x] Deterministic policies: `duplicate_tool_protection`, `retry_budget`, `cost_budget`, `stall_protection`, `loop_protection`
- [x] Actions: `warn`, `block` (dedupe), `retry`, `pause`, `stop` (preserves trace + `run.failed`)
- [x] `BudgetTracker` with `CounterBackend` port (in-memory default, Redis optional)
- [x] Full audit trail: `intervention.applied` + `human_review_required`
- [x] Safe default: observe unless `SUPERVISOR_ENFORCE=true` / `Supervisor(enforce=True)`
- [x] Demo opt-in via `SUPERVISOR_ENFORCE`; CLI/OTel/audit observable
- [x] Tests: policy evaluate, enforcement, budgets, SDK enforcement, adapter

### Phase 2 verification (2026-07-14)

- `pytest` — **60 passed** (policy, enforcement, budgets, sdk, analytics, adapters, cli, demo)
- `ruff check` / `ruff format` — clean
- `mypy src/supervisor` — clean (strict)
- Under `SUPERVISOR_ENFORCE=true` the expensive demo scenario is stopped on retry-budget exhaustion; success scenario is unaffected (non-interference).

## Phase 3 deliverables

- [x] `PlanTier` vocabulary + deterministic `select_tier(task)` (risk baseline, cost bump, critical clamp)
- [x] `Planner.build_plan` → `ExecutionPlan` (tier options with cost/latency multipliers + steps; one `recommended`)
- [x] `ContextEngine.build_manifest` → role-sensitive `ContextManifest` (included/excluded/compressed + estimated tokens)
- [x] `ModelRouter.select` → tier-aware `RoutingDecision` from a `ModelRegistry` (capability + tier + allowed_models, deterministic, safe fallback)
- [x] SDK wiring: `Supervisor.plan()`, `route_model()`, `model(routing=)`, `context(master_context=)`, `start_run` carries `tier`
- [x] `RunSummary.plan_tier` + `routing[]` from routed `model.requested` events
- [x] Demo opt-in via `SUPERVISOR_PLAN=1` (researcher/analyst/writer wired through planner/router/context engine)
- [x] Tests: planning, context, routing, SDK integration; ADR-008, ADR-009

### Phase 3 verification (2026-07-14)

- `pytest` — **79 passed** (planning, context, routing, sdk, analytics, policy, enforcement, budgets, adapters, cli, demo)
- `ruff check` — clean
- `mypy src/supervisor` — clean (strict)
- `SUPERVISOR_PLAN=1` demo emits `tier` on `run.started`, per-step `context.attached` manifests, and `routing_tier` on routed `model.requested`; `RunSummary` reports `plan_tier` and `routing`.

## Phase 1 approval gate — completed

```
Phase 1 implemented.

Goal: Make an agent run inspectable without changing its behavior. ✓

Scope delivered: Python SDK, LangGraph adapter implementation, automatic event
       collection, cost aggregation, observe-only policy evaluation,
       minimal run explorer CLI, OTel export implementation.

Not in scope (deferred): Enforcement, routing, context mutation, full UI.
```

## Assumptions register

| Assumption | Risk if wrong |
|---|---|
| LangGraph API stable at pinned version | Adapter may need updates |
| Synthetic traces represent real waste | Fixtures refined after partner traces |
| Mock pricing sufficient for demos | Real pricing added in Phase 1 |
