# Roadmap

Phase-by-phase delivery per the [master prompt](AI_DEVELOPER_MASTER_PROMPT.md) and [blueprint](AI_RUNTIME_SUPERVISOR_BLUEPRINT.md).

| Phase | Name | Status | Exit criteria summary |
|---|---|---|---|
| 0 | Discovery, repository setup, baseline | **Complete (verified)** | Contracts, docs, synthetic workflow, fixtures, metrics defined; `pytest`/ruff/mypy green |
| 1 | Observe and explain | Proposed — plan ready | SDK, automatic events, timeline, observe-only policies ([plan](phase-1-plan.md)) |
| 2 | Deterministic protection | Not started | Budgets, duplicate/loop detection, intervention modes |
| 3 | Planner, context, routing | Not started | Cost tiers, context manifests, model routing, validation |
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

## Confirmed decisions

| Decision | Choice |
|---|---|
| First framework adapter | LangGraph |
| First workflow | Cited market-research |
| Traces | Synthetic fixtures |
| Observability | OTel interface only; vendor deferred |
| Model access | LiteLLM mock; paid opt-in |

## Explicit deferrals

- SDK instrumentation (Phase 1)
- Policy enforcement (Phase 2)
- Cost tier planner and routing (Phase 3)
- Next.js control plane UI (Phase 1 minimal API/CLI first)
- PostgreSQL/Redis/MinIO deep wiring (Phase 1+)
- Real LiteLLM provider calls (opt-in)
- Langfuse/Phoenix/LangSmith export (Phase 1+)

## Next: Phase 1 approval gate

```
Phase 1 is ready to begin.

Goal: Make an agent run inspectable without changing its behavior.

Scope: Python SDK, LangGraph adapter implementation, automatic event
       collection, cost aggregation, observe-only policy evaluation,
       minimal run explorer API/CLI, OTel export implementation.

Not in scope: Enforcement, routing, context mutation, full UI.

May I implement Phase 1 now?
```

Approval required before starting Phase 1.

## Assumptions register

| Assumption | Risk if wrong |
|---|---|
| LangGraph API stable at pinned version | Adapter may need updates |
| Synthetic traces represent real waste | Fixtures refined after partner traces |
| Mock pricing sufficient for demos | Real pricing added in Phase 1 |
