# AI Runtime Supervisor

Control plane for production AI-agent work. The Supervisor plans, contextualizes, routes, governs, and verifies each agent run—reducing wasted spend and unreliable outcomes without requiring teams to rebuild their applications.

**Current phase:** Phase 5 — Memory lifecycle & retrieval governance (implemented, pending release).

## What exists today

- Versioned data contracts (task, events, plan, policy, validation)
- Python SDK (`Supervisor` + `RunCollector`) for zero-touch event emission
- LangGraph adapter with automatic callback-based instrumentation
- Synthetic cited market-research LangGraph demo workflow with mock tools
- Representative trace fixtures for success, expensive, and failed-validation runs
- Observe-only policy engine (duplicate detection, retry budget, cost overrun, validation)
- **Opt-in enforcement** (Phase 2): block / retry / pause / stop with full audit trail
- Budget tracking (`BudgetTracker`, in-memory default, Redis backend port)
- Run-explorer CLI and OpenTelemetry export (Console + OTLP)
- **Advisory planning** (Phase 3): tier selection, per-step context manifests, capability+tier model routing
- **Adaptive optimization** (Phase 4): semantic near-duplicate detection + idempotent result caching (`SUPERVISOR_OPTIMIZE`, dry-run default)
- **Memory governance** (Phase 5): memory store + scoring + governor (`memory.retrieved`/`memory.expired` manifest) with audited expiry, no automatic deletion (`SUPERVISOR_MEMORY`)
- Local development environment (Docker Compose + pytest)

**Not yet implemented:** control-plane UI (planning/routing/optimization are opt-in by default).

## Quickstart

### Prerequisites

- Python 3.12+
- Docker Desktop (optional, for Postgres/Redis/MinIO scaffold)

### Setup (Windows)

```powershell
.\scripts\dev.ps1
.\.venv\Scripts\Activate.ps1
```

### Run tests

```powershell
pytest -v
```

### Run the demo workflow

```powershell
# Successful run
python -m examples.cited_market_research.agent --scenario success

# All scenarios + write trace fixtures
python -m examples.cited_market_research.agent --scenario all --write-fixtures

# Phase 1 run explorer (inspect a captured run)
python -m supervisor.cli explore --run fixtures/traces/expensive_run.json --policy

# Live run with policy observations and OTel export
python -m supervisor.cli explore --live --scenario expensive --policy --otel

# Phase 3 advisory planning (plan tier + context manifests + model routing)
$env:SUPERVISOR_PLAN=1
python -m examples.cited_market_research.agent --scenario all

# Phase 4 adaptive optimization (semantic dedup + caching)
$env:SUPERVISOR_OPTIMIZE=1                       # dry-run: recommend only
$env:SUPERVISOR_OPTIMIZE_MODE=active             # serve idempotent cache hits
python -m examples.cited_market_research.agent --scenario expensive

# Phase 5 memory governance (memory-backed retrieval)
$env:SUPERVISOR_MEMORY=1
python -m examples.cited_market_research.agent --scenario all
```

No API keys required. Mock models and tools are used by default.

## Repository layout

```text
src/supervisor/          Core contracts, SDK, adapters, analytics, policy, telemetry, CLI
examples/                Runnable demo workflows
fixtures/traces/         Synthetic trace JSON for tests and baselines
docs/                    Architecture, contracts, roadmap, ADRs
docs/development/        Source master prompt, blueprint, phase plans
templates/               Baseline measurement templates
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System components and boundaries |
| [Runtime chain](docs/runtime-chain.md) | Stage-by-stage runtime flow |
| [Data contracts](docs/data-contracts.md) | Schema reference |
| [Roadmap](docs/roadmap.md) | Phase status and deferrals |
| [Integrations](docs/integrations.md) | Adapter contracts |
| [Operations](docs/operations.md) | Local dev, commands, runbooks |
| [Policy engine](docs/policy-engine.md) | Policy modes and Phase 1 observe policies |

## First workflow

**Cited market-research agent** — produces a competitor brief with citations, comparison table, and validation against a task contract. See `examples/cited_market_research/`.

## License

MIT
