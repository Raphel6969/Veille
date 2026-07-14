# Operations

## Local development

### One-command setup (Windows)

```powershell
.\scripts\dev.ps1
```

Options:

- `-SkipDocker` — skip Postgres/Redis/MinIO
- `-SkipInstall` — skip pip install

### Manual setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
docker compose up -d
```

### Infrastructure services

| Service | Port | Purpose |
|---|---|---|
| PostgreSQL | 5432 | Run metadata (Phase 1+) |
| Redis | 6379 | Budgets/counters (Phase 2+) |
| MinIO | 9000 / 9001 | Artifact storage (Phase 1+) |

Phase 1 does not require these services for tests or the demo workflow (observability is local/OTel-export).

## Common commands

```powershell
pytest -v
ruff check src tests examples
ruff format src tests examples
mypy src/supervisor
python -m examples.cited_market_research.agent --scenario all --write-fixtures

# Phase 1 run explorer
python -m supervisor.cli explore --run fixtures/traces/expensive_run.json
python -m supervisor.cli explore --live --scenario expensive --policy --otel

# Phase 3 advisory planning (plan + context + routing)
$env:SUPERVISOR_PLAN=1
python -m examples.cited_market_research.agent --scenario all
```

```powershell
# Phase 4 adaptive optimization (semantic dedup + caching)
$env:SUPERVISOR_OPTIMIZE=1                       # dry-run: recommends only
$env:SUPERVISOR_OPTIMIZE_MODE=active             # serve idempotent cache hits
$env:SUPERVISOR_CACHE_APPROVED=1                 # partner-confirmation gate (3+ confirmations)
python -m examples.cited_market_research.agent --scenario expensive
```

```powershell
# Phase 5 memory lifecycle & governance (memory-backed retrieval)
$env:SUPERVISOR_MEMORY=1
python -m examples.cited_market_research.agent --scenario all
```

## Veille Console CLI

The `veille` CLI bundles all console operations. Install with `pip install -e ".[ui]"` to get the web server.

```powershell
# Doctor — report environment + safe-config status
veille doctor

# List / validate provider connections
veille connections
veille connections validate openai
veille connections validate openai --real

# List registered workflows
veille workflows
veille workflows inspect cited_market_research

# Execute a registered workflow through the runtime
veille run cited_market_research --input '{"scenario":"success"}'
veille run real_world_demo --input '{"scenario":"success"}' --yes

# List / show saved runs
veille runs
veille runs show <run-id>

# List registered providers
veille providers list

# List installed adapters
veille adapters list

# Run built-in demos
veille demo mock
veille demo real-world --cross-run

# Start the FastAPI web server (serves the React UI on http://127.0.0.1:8000)
veille serve

# Inspect a trace fixture
veille explore --run fixtures/traces/success_run.json
veille explore --live --scenario expensive --policy
```

### Safety rules (built-in)

- Secrets are never printed, committed, returned, or stored by the console.
- Credentials are masked (`…abcd`), never revealed.
- Confirmation is required before:
  - Paid API calls (real mode asks `--yes`)
  - Enabling enforcement / optimization / cross-run cache
  - Persistent credential changes
- Defaults are always **mock** providers, **mock** workflows, and **mock** tools.
- Missing credentials print guidance and continue in mock — the console never fails at startup.

## CI

GitHub Actions runs on push/PR to `main` or `master`:

1. Ruff lint and format check
2. Mypy on `src/supervisor`
3. Pytest

## Troubleshooting

| Issue | Resolution |
|---|---|---|
| `ModuleNotFoundError: examples` | Activate venv; run from repo root |
| Docker compose fails | Use `-SkipDocker` or install Docker Desktop |
| LangGraph import errors | `pip install -e ".[dev]"` |
| Mypy errors on langgraph | Overrides ignore missing stubs |
| `veille: command not found` | Run `pip install -e ".[ui]"` to register the console entry point |
| `ModuleNotFoundError: fastapi` | Run `pip install -e ".[ui]"` to install web dependencies |
| Web UI blank / API unreachable | Start the backend first (`veille serve`); the Vite dev server proxies `/api` to `127.0.0.1:8000` |

## Logging

Set `LOG_LEVEL` in `.env`. The demo and `run-explorer` print summaries to stdout.

## Runbooks

- **Enabling observe-mode policies:** they run by default in `evaluate_observe`; use `python -m supervisor.cli explore --live --scenario expensive --policy` to view matches.
- **Enabling enforcement (Phase 2):** set `SUPERVISOR_ENFORCE=true` (or construct `Supervisor(enforce=True)`). Policies act per their configured action (`block`/`stop`/`pause`). Default is observe — enforcement never changes behavior unless explicitly enabled.
- **Enabling advisory planning (Phase 3):** set `SUPERVISOR_PLAN=1` (or call `Supervisor.plan()` before `start_run`). This annotates runs with a `PlanTier` (`run.started.tier`), builds per-step context manifests, and routes models by capability + tier. Default is off — planning is purely advisory and never blocks a run. The plan tier is visible in `RunSummary.plan_tier` and routed calls in `RunSummary.routing`.
- **Enabling optimization (Phase 4):** set `SUPERVISOR_OPTIMIZE=1` (default sub-mode `dry_run` → recommends only) and optionally `SUPERVISOR_OPTIMIZE_MODE=active` to serve idempotent cache hits. Detection marks `tool.requested` / `model.requested` with `match_type` (`exact`/`semantic`) + `similarity`; dry-run emits `optimization.recommended`, active emits `optimization.applied` and skips re-execution. Only allowlisted `idempotent=True` tools (default `search_competitors`) and `cacheable=True` model calls are cached. **Serving additionally requires the partner-confirmation gate** (see below). `RunSummary` reports `cache_hits`, `cache_served`, `semantic_duplicates`, `estimated_savings_usd`.
- **Approved cache policy (v0.2.0, ADR-012):** the cache serves only **identical normalized inputs** (exact match); semantic/near-duplicate matches are recommended but never served (uncertain → re-execute). Cache keys include tenant/project, tool version, policy version, and authorization/context boundaries, so results are reused only within the same isolation + governance context. Default TTL is **300s**; expired/uncertain results always re-execute. Serving is gated behind partner confirmation: `SUPERVISOR_CACHE_APPROVED=1` (demo/test override) or `SUPERVISOR_CACHE_CONFIRMATIONS=N` with `N >= 3` (default threshold). Dry-run recommendations are emitted regardless of the gate. Move to cross-run caching only after 3–5 partners confirm the cacheable unit and freshness policy with no material stale-result concern.
- **Reading the audit trail:** every action emits an `intervention.applied` event (with `action`, `policy_id`, `reason`, `human_review_required`); the run-explorer `--policy` flag surfaces them, and OTel export forwards them as span attributes.
- **Enabling memory governance (Phase 5):** set `SUPERVISOR_MEMORY=1` to store and retrieve memories via `Supervisor.remember`/`retrieve_memory`. Off-mode keeps Phase 4 behavior; `retrieve_memory` is a no-op passthrough. `MemoryGovernor` scores candidates (recency/usage/provenance/confidence + role weights), flags `stale` (recency/confidence) and `drift` (content hash vs baseline), and emits a `memory.retrieved` manifest with `included`/`excluded`/`stale`/`drift`/`scores`/`reason`. `expire_memory()` surfaces TTL-elapsed records as `memory.expired` **without deleting**; `forget_memory(id)` removes explicitly (audited). Automatic deletion is deferred. `RunSummary` reports `memories_retrieved`, `memories_stale`, `memories_drift`, `memories_expired`.
- **Exporting traces to OTel backend:** `OtlpExporter(endpoint=...).export_events(events)` or `--otel` on the explorer.
