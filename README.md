# AI Runtime Supervisor / Veille Console

Control plane for production AI-agent work. The Supervisor plans, contextualizes, routes, governs, and verifies each agent run—reducing wasted spend and unreliable outcomes without requiring teams to rebuild their applications.

**Current release:** [0.3.1](https://pypi.org/project/veille-supervisor/0.3.1/) — Phases 1–5 + **Local Integration Console**. Event schema `0.2.0`. All capabilities are opt-in and off by default.

## Quickstart (2 minutes)

```bash
pip install veille-supervisor
veille demo              # run the mock demo agent
veille explore           # browse timeline + graphs
veille serve             # web UI at http://localhost:8010
```

No API keys. No config. Just works.

## What exists today

- Versioned data contracts (task, events, plan, policy, validation)
- Python SDK (`Supervisor` + `RunCollector`) for zero-touch event emission
- LangGraph adapter with automatic callback-based instrumentation
- **OpenAI Agents SDK adapter** and **OpenAI Responses API adapter** (skeleton)
- **Model provider port** with 8 provider drivers (LiteLLM, OpenAI, Anthropic, Gemini, OpenRouter, Ollama, LM Studio, OpenAI-compatible)
- Synthetic cited market-research LangGraph demo workflow with mock tools
- Representative trace fixtures for success, expensive, and failed-validation runs
- Observe-only policy engine (duplicate detection, retry budget, cost overrun, validation)
- **Opt-in enforcement** (Phase 2): block / retry / pause / stop with full audit trail
- Budget tracking (`BudgetTracker`, in-memory default, Redis backend port)
- Run-explorer CLI and OpenTelemetry export (Console + OTLP)
- **Advisory planning** (Phase 3): tier selection, per-step context manifests, capability+tier model routing
- **Adaptive optimization** (Phase 4): semantic near-duplicate detection + idempotent result caching (`SUPERVISOR_OPTIMIZE`, dry-run default)
- **Memory governance** (Phase 5): memory store + scoring + governor (`memory.retrieved`/`memory.expired` manifest) with audited expiry, no automatic deletion (`SUPERVISOR_MEMORY`)
- **Local Integration Console** (`veille` CLI + FastAPI + React web UI) — register workflows, connect providers, run live, inspect execution
- Local development environment (Docker Compose + pytest)

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

### Use the console

```powershell
# Doctor — environment + safe-config report
veille doctor

# List provider connections
veille connections
veille connections validate openai

# List registered workflows
veille workflows

# Run the mock demo
veille demo mock

# Run the real-world demo
veille demo real-world

# List saved runs
veille runs

# Run an arbitrary registered workflow
veille run cited_market_research --input '{"scenario":"success"}'

# Start the web UI (then open http://127.0.0.1:8000)
veille serve
```

### Run the classic demo workflow

```powershell
# Successful run
python -m examples.cited_market_research.agent --scenario success

# All scenarios + write trace fixtures
python -m examples.cited_market_research.agent --scenario all --write-fixtures

# Phase 1 run explorer (inspect a captured run)
python -m supervisor.cli explore --run fixtures/traces/expensive_run.json --policy

# Live run with policy observations and OTel export
python -m supervisor.cli explore --live --scenario expensive --policy --otel
```

No API keys required. Mock models and tools are used by default.

## Repository layout

```text
src/supervisor/          Core contracts, SDK, adapters, analytics, policy, telemetry, CLI, console
examples/                Runnable demo workflows
fixtures/traces/         Synthetic trace JSON for tests and baselines
docs/                    Architecture, contracts, roadmap, ADRs
docs/development/        Source master prompt, blueprint, phase plans
ui/                      React+TypeScript+Vite web UI (veille console frontend)
templates/               Baseline measurement templates
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System components and boundaries |
| [Runtime chain](docs/runtime-chain.md) | Stage-by-stage runtime flow |
| [Data contracts](docs/data-contracts.md) | Schema reference |
| [Roadmap](docs/roadmap.md) | Phase status and deferrals |
| [Integrations](docs/integrations.md) | Adapter contracts + provider drivers |
| [Operations](docs/operations.md) | Local dev, commands, runbooks |
| [Policy engine](docs/policy-engine.md) | Policy modes and Phase 1 observe policies |
| [ADR-013](docs/adr/013-local-integration-console.md) | Local Integration Console design |

### Setup guides

| Guide | Description |
|---|---|
| [Safe local setup](docs/guides/safe-local-setup.md) | Running with mock providers (default) |
| [Mock demo walkthrough](docs/guides/mock-demo.md) | End-to-end mock demo |
| [Real provider setup](docs/guides/real-provider-setup.md) | Setting up real model providers |
| [OpenRouter integration](docs/guides/openrouter-setup.md) | Using OpenRouter as a gateway |
| [OpenAI Agents SDK](docs/guides/openai-agents-sdk.md) | Running an OpenAI Agents SDK workflow |
| [LiteLLM integration](docs/guides/litellm-integration.md) | Using LiteLLM for multi-provider access |

## License

MIT
