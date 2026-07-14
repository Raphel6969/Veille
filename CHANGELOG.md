# Changelog

All notable changes are documented here. This project follows phase-based delivery.

## [Unreleased]

### Phase 3 — Planner, context, routing (implemented, pending release)

- **Plan tiers** (`src/supervisor/contracts/plan.py`): `PlanTier` (minimum / balanced /
  high_quality / maximum_assurance), `TierEstimate`, `PlanStep`, `ExecutionPlan`.
- **Planner** (`src/supervisor/planning/planner.py`): deterministic `select_tier(task)`
  (risk baseline, cost bump, critical clamp) and `Planner.build_plan` → `ExecutionPlan`
  with tier options (cost/latency multipliers) and steps; one option marked `recommended`.
- **Context engine** (`src/supervisor/context/engine.py`): `ContextEngine.build_manifest`
  builds a role-sensitive `ContextManifest` (included / excluded / compressed slices +
  estimated tokens) deterministically from a master context.
- **Model routing** (`src/supervisor/routing/router.py`): `ModelRegistry` + `ModelRouter.select`
  returns a tier-aware `RoutingDecision` (capability + tier + allowed_models; deterministic;
  safe static fallback for empty registries).
- **SDK wiring** (`src/supervisor/sdk/supervisor.py`): `Supervisor.plan()`, `route_model()`,
  `model(routing=)`, `context(master_context=)`; `start_run` records the planned `tier`.
- **Run summary** (`src/supervisor/analytics/run_summary.py`): `RunSummary.plan_tier` and
  `routing[]` derived from routed `model.requested` events (`routing_tier` /
  `routing_capability` / `routing_reason`).
- **Advisory by default:** gated behind `SUPERVISOR_PLAN=1` (mirroring `SUPERVISOR_ENFORCE`);
  never blocks or rewrites execution.
- **Demo:** `examples/cited_market_research/agent.py` wires researcher/analyst/writer through
  the planner, router, and context engine when `SUPERVISOR_PLAN=1`.
- **Tests:** planning, context, routing, SDK integration — 79 total.
- **Docs:** ADR-008 (tier/cost model), ADR-009 (routing), data-contracts / architecture /
  runtime-chain / integrations / operations / roadmap / README updates.

### Phase 2 — Deterministic protection (implemented, pending release)

- **Enforcement engine** (`src/supervisor/policy/enforcement.py`): `Enforcer` +
  `GuardDecision`; exceptions `InterventionError` / `StopRun` / `PauseForApproval` /
  `BlockedByPolicy`. Detection (`evaluate`) separated from action.
- **Deterministic policies** (`src/supervisor/policy/engine.py`): `duplicate_tool_protection`
  (block/dedupe), `retry_budget` (stop), `cost_budget` (stop), `stall_protection` (stop),
  `loop_protection` (stop). Default mode `enforce`; gated by `Supervisor(enforce=True)`
  or `SUPERVISOR_ENFORCE=true`.
- **Budgets** (`src/supervisor/policy/budgets.py`): `BudgetTracker` behind a
  `CounterBackend` port (in-memory default, Redis optional).
- **SDK guards** (`src/supervisor/sdk/supervisor.py`): `tool()` dedupes blocked duplicates,
  `retry()` stops on budget exhaustion; `emit_intervention` / `consult` / `act` helpers.
- **Audit:** every action emits `intervention.applied` with `action`, `policy_id`, `reason`,
  and `human_review_required`.
- **Safe default:** observe mode is byte-for-byte identical to Phase 1.
- **Demo:** opt-in enforcement via `SUPERVISOR_ENFORCE`; the expensive scenario is stopped
  on retry-budget exhaustion.
- **Tests:** policy evaluate, enforcement, budgets, SDK enforcement, adapter — 60 total.
- **Docs:** ADR-006 (enforcement model), ADR-007 (budget backend), policy-engine /
  data-contracts / roadmap updates.

### Phase 1 — Observe and explain (implemented, pending release)

- **Python SDK** (`src/supervisor/sdk/`): `Supervisor` emission helpers
  (`start_run`, `finish_run`, `model`, `tool`, `retry`, `context`, `node`,
  `emit_validation`) and `RunCollector` aggregation.
- **LangGraph adapter** (`src/supervisor/adapters/langgraph/adapter.py`): callback-based
  automatic instrumentation; agent authors call `adapter.attach(graph)` only.
- **Run summary analytics** (`src/supervisor/analytics/run_summary.py`): `summarize()`
  produces a `RunSummary` (tool call counts, duplicates, retries, cost, timeline,
  policy observations, validation result).
- **Observe-only policy engine** (`src/supervisor/policy/engine.py`): `evaluate_observe`
  detects duplicate tool calls, retry storms (budget 5), cost overruns, and validation
  failures; emits `policy.triggered` events. Never alters execution.
- **OTel exporter** (`src/supervisor/telemetry/exporter.py`): `ConsoleOTelExporter`
  (default) and `OtlpExporter` (OTLP/gRPC) via `event_to_span`.
- **Run-explorer CLI** (`src/supervisor/cli.py`): `explore` subcommand for fixtures
  (`--run`) or live runs (`--live --scenario`) with `--policy` and `--otel` flags.
- **Demo refactor** (`examples/cited_market_research/agent.py`): now uses the SDK;
  `trace_capture.py` reduced to `validate_brief` input validation only.
- **Tests:** sdk, analytics, policy, telemetry mapping, langgraph adapter, cli, and
  demo smoke — 39 tests passing.
- **Docs:** ADR-004 (LangGraph callbacks), ADR-005 (OTel mapping), event attributes
  registry in `data-contracts.md`, updated architecture/runtime-chain/policy-engine/
  integrations/operations/roadmap.
- **Quality gates:** `ruff`, `mypy --strict`, `pytest` all green on Python 3.14.

## [0.1.0] — Phase 0 baseline (2026-07-14)

- Data contracts v0.1: task contract, run events, validation report.
- Adapter ports: LangGraph (interface), LiteLLM mock, OTel interface.
- Synthetic cited market-research LangGraph workflow.
- Trace fixtures (success, expensive, failed_validation).
- Documentation system, docker compose, CI, dev scripts.
