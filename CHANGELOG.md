# Changelog

All notable changes are documented here. This project follows phase-based delivery.

## [Unreleased]

### Approved cache policy (post-0.2.0, ADR-012)

- **`supervisor/optimize/policy.py`**: `CachePolicy` + `build_cache_key` encode the
  three partner-validated cache rules. `search_competitors` is cacheable only for
  **identical normalized inputs** (exact); semantic/near-duplicate matches are
  recommended, never served. Cache keys include **tenant/project, tool version,
  policy version, and authorization/context boundaries**. Default **300s TTL**;
  expired/uncertain results re-execute. Serving is gated behind partner
  confirmation (`SUPERVISOR_CACHE_APPROVED` override or `SUPERVISOR_CACHE_CONFIRMATIONS >= 3`).
- **SDK wiring** (`src/supervisor/sdk/supervisor.py`): `tool()`/`model()` serve only
  when approved, allowlisted, idempotent, and exact; composite key + TTL applied.
- **Adaptive rerouting remains advisory-only** (unchanged).
- Tests: `tests/sdk/test_cache_policy.py` (6 rules/gate tests); 125 total passing.

## [0.2.0] — Phases 1–5 (2026-07-14)

### Phase 5 — Memory lifecycle & retrieval governance (implemented)

- **Memory store** (`src/supervisor/memory/store.py`): `MemoryBackend` port + `InMemoryMemoryStore` (tenant-isolated, no deps); `MemoryRecord` with tier (working/short/long/archive), provenance, confidence, TTL, and baseline hash for drift; `content_hash` util. Mem0/Letta/customer RAG attach behind the port.
- **Scoring** (`src/supervisor/memory/scoring.py`): `score(record, now, role_weights)` combines recency (exponential decay), usage, provenance quality, and confidence; metadata-driven, no embeddings by default. `default_role_weights` nudge tier preference by role.
- **Governor** (`src/supervisor/memory/governor.py`): `MemoryManifest` + `MemoryGovernor.retrieve(...)` scores candidates, flags `stale` (recency/confidence) and `drift` (content hash vs baseline), and emits an included/excluded/stale/drift/scores/reason manifest. `expire_due(...)` surfaces TTL-elapsed records for **audited** removal — no automatic deletion.
- **Event schema 0.2.0 (additive):** `memory.retrieved` carries the governance manifest; new `memory.expired` records expiry candidates and explicit removals.
- **SDK wiring** (`src/supervisor/sdk/supervisor.py`): `Supervisor.remember`, `retrieve_memory`, `expire_memory`, `forget_memory`; gated by `SUPERVISOR_MEMORY=1`. Off-mode `retrieve_memory` is a no-op passthrough (identical to Phase 4).
- **Run summary** (`src/supervisor/analytics/run_summary.py`): `memories_retrieved`, `memories_stale`, `memories_drift`, `memories_expired`.
- **Demo:** researcher node stores a working memory and retrieves it on subsequent calls when `SUPERVISOR_MEMORY=1`.
- **Tests:** store, scoring, governor, SDK memory, demo memory — 119 total.
- **Docs:** ADR-011 (memory governance), data-contracts / architecture / runtime-chain / integrations / operations / roadmap / README updates.

### Phase 4 — Semantic dedup and adaptive caching (implemented)

- **Semantic key** (`src/supervisor/optimize/keys.py`): `ShingleSemanticKey` tokenizes input into word-shingles and compares with Jaccard similarity (default threshold 0.85). Embedding backend is a future `SemanticKey` port.
- **Near-duplicate detector** (`src/supervisor/optimize/dedup.py`): `DuplicateDetector` returns `DuplicateMatch` (`exact` | `semantic`, `similarity`, `cache_key`) for in-run `(tool, input)` calls.
- **Cache backend** (`src/supervisor/optimize/cache.py`): `CacheBackend` port with `InMemoryCache` (bounded LRU-ish FIFO + per-entry TTL). Redis is a later backend behind the same port.
- **Event schema 0.2.0** (`src/supervisor/contracts/events.py`): new `optimization.recommended` / `optimization.applied`; `tool.requested` / `model.requested` gain `match_type` + `similarity`; `optimization.*` carry `cache_key`, `cache_hit`, `estimated_savings_usd`. Additive over 0.1.0.
- **SDK wiring** (`src/supervisor/sdk/supervisor.py`): `Supervisor.tool(idempotent=)` / `model(cacheable=)` consult detector + cache. Dry-run recommends; active serves idempotent cache hits and skips re-execution. Gated by `SUPERVISOR_OPTIMIZE` (`dry_run` default, `SUPERVISOR_OPTIMIZE_MODE=active`).
- **Run summary** (`src/supervisor/analytics/run_summary.py`): `cache_hits`, `cache_served`, `semantic_duplicates`, `estimated_savings_usd`.
- **Demo:** idempotent tool calls are cached when optimization is enabled; expensive scenario serves the duplicate `search_competitors` from cache in active mode.
- **Tests:** keys, dedup, cache, SDK dry-run/active, demo optimization — 99 total.
- **Docs:** ADR-010 (semantic dedup + caching + dry-run opt-in), data-contracts / architecture / runtime-chain / integrations / operations / roadmap / README updates.

### Phase 3 — Planner, context, routing (implemented)

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

### Phase 2 — Deterministic protection (implemented)

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

### Phase 1 — Observe and explain (implemented)

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
