# Roadmap

Phase-by-phase delivery per the [master prompt](development/AI_DEVELOPER_MASTER_PROMPT.md) and [blueprint](development/AI_RUNTIME_SUPERVISOR_BLUEPRINT.md).

| Phase | Name | Status | Exit criteria summary |
|---|---|---|---|
| 0 | Discovery, repository setup, baseline | **Complete (verified)** | Contracts, docs, synthetic workflow, fixtures, metrics defined; `pytest`/ruff/mypy green |
| 1 | Observe and explain | **Implemented (pending release)** | SDK, automatic events, timeline, observe-only policies ([plan](development/phase-1-plan.md)) |
| 2 | Deterministic protection | **Implemented (pending release)** | Budgets, duplicate/loop detection, intervention modes ([plan](development/phase-2-plan.md)) |
| 3 | Planner, context, routing | **Implemented (pending release)** | Cost tiers, context manifests, model routing, validation ([plan](development/phase-3-plan.md)) |
| 4 | Adaptive optimization | **Implemented (pending release)** | Semantic dedup, adaptive caching, dry-run opt-in ([plan](development/phase-4-plan.md)) |
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
- Learned/adaptive tier rerouting and cost-latency auto-tune loop (deferred Phase 4 workstream)
- Embedding-API semantic key backend (deferred; default is cheap shingle/Jaccard)
- Durable (Redis) cache backend (deferred; in-memory default behind `CacheBackend` port)
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

## Phase 4 deliverables

- [x] `SemanticKey` port + `ShingleSemanticKey` (word-shingle Jaccard, dependency-free)
- [x] `DuplicateDetector` (exact + semantic near-duplicate, configurable threshold)
- [x] `CacheBackend` port + `InMemoryCache` (bounded LRU-ish FIFO + per-entry TTL)
- [x] Event schema **0.2.0**: `optimization.recommended` / `optimization.applied`; `match_type` / `similarity` on `tool.requested` / `model.requested`
- [x] SDK `Supervisor.tool(idempotent=)` / `model(cacheable=)` with dry-run + active modes (`SUPERVISOR_OPTIMIZE`, `SUPERVISOR_OPTIMIZE_MODE`)
- [x] `RunSummary` cache/savings accounting (`cache_hits`, `cache_served`, `semantic_duplicates`, `estimated_savings_usd`)
- [x] Demo idempotent tools cached when optimization is enabled
- [x] Tests: keys, dedup, cache, SDK dry-run/active, demo optimization; ADR-010

### Phase 4 verification (2026-07-14)

- `pytest` — **99 passed** (optimize keys/dedup/cache, SDK dry-run/active, demo optimization, planning, context, routing, policy, enforcement, budgets, adapters, cli)
- `ruff check` — clean
- `mypy src/supervisor` — clean (strict)
- Under `SUPERVISOR_OPTIMIZE=1 SUPERVISOR_OPTIMIZE_MODE=active` the expensive demo scenario serves the duplicate `search_competitors` call from cache (`optimization.applied`), reducing measured cost (0.0238 → 0.0218); dry-run emits `optimization.recommended` and leaves execution unchanged.
- Works without API keys on Python 3.14.

## Phase 5 deliverables (Memory lifecycle & governance — opt-in; enterprise deferred)

- [x] `MemoryBackend` port + `InMemoryMemoryStore` (tenant-isolated, no deps)
- [x] `MemoryRecord` (tier working/short/long/archive, provenance, confidence, TTL, baseline hash for drift)
- [x] `score()` governance (recency decay + usage + provenance + confidence, role weights)
- [x] `MemoryGovernor.retrieve()` → `MemoryManifest` (included/excluded/stale/drift/scores/reason); audited expiry via `expire_due()`
- [x] Event schema 0.2.0 additive: `memory.retrieved` (manifest) + `memory.expired` (audited)
- [x] SDK `Supervisor.remember` / `retrieve_memory` / `expire_memory` / `forget_memory` (`SUPERVISOR_MEMORY=1`, off = passthrough)
- [x] `RunSummary` memory accounting (`memories_retrieved`, `memories_stale`, `memories_drift`, `memories_expired`)
- [x] Demo memory-backed retrieval opt-in for the researcher node
- [x] Tests: store, scoring, governor, SDK memory, demo memory; ADR-011

### Phase 5 verification (2026-07-14)

- `pytest` — **119 passed** (memory store/scoring/governor, SDK memory, demo memory, + prior suites)
- `ruff check` — clean
- `mypy src/supervisor` — clean (strict)
- Under `SUPERVISOR_MEMORY=1` the demo researcher node stores a working memory and retrieves it on the next call; off-mode emits no `memory.*` events and leaves behavior unchanged.
- Works without API keys on Python 3.14.

## Post-0.2.0 — Approved cache policy (ADR-012, on `pre_dev`)

The design-partner program validated three explicit cache rules, now enforced:

- `search_competitors` cacheable **only for identical normalized inputs** (exact); semantic/near-duplicate → recommend, never serve.
- Cache keys include **tenant/project, tool version, policy version, auth/context boundaries**.
- Default **300s TTL**; expired/uncertain results re-execute. Serving gated behind **partner confirmation** (`SUPERVISOR_CACHE_APPROVED=1` or `SUPERVISOR_CACHE_CONFIRMATIONS >= 3`).
- Adaptive rerouting stays **advisory-only**.
- `pytest` — **125 passed** (added `tests/sdk/test_cache_policy.py`); ruff + mypy clean.

**Rollout gate:** build cross-run (durable) caching only after **3–5 partners confirm**
the cacheable unit (Q3) and freshness policy (Q4) with no material stale-result concern.

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
