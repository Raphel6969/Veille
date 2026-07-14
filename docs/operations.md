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

## CI

GitHub Actions runs on push/PR to `main` or `master`:

1. Ruff lint and format check
2. Mypy on `src/supervisor`
3. Pytest

## Troubleshooting

| Issue | Resolution |
|---|---|
| `ModuleNotFoundError: examples` | Activate venv; run from repo root |
| Docker compose fails | Use `-SkipDocker` or install Docker Desktop |
| LangGraph import errors | `pip install -e ".[dev]"` |
| Mypy errors on langgraph | Overrides ignore missing stubs |

## Logging

Set `LOG_LEVEL` in `.env`. The demo and `run-explorer` print summaries to stdout.

## Runbooks

- **Enabling observe-mode policies:** they run by default in `evaluate_observe`; use `python -m supervisor.cli explore --live --scenario expensive --policy` to view matches.
- **Enabling enforcement (Phase 2):** set `SUPERVISOR_ENFORCE=true` (or construct `Supervisor(enforce=True)`). Policies act per their configured action (`block`/`stop`/`pause`). Default is observe — enforcement never changes behavior unless explicitly enabled.
- **Enabling advisory planning (Phase 3):** set `SUPERVISOR_PLAN=1` (or call `Supervisor.plan()` before `start_run`). This annotates runs with a `PlanTier` (`run.started.tier`), builds per-step context manifests, and routes models by capability + tier. Default is off — planning is purely advisory and never blocks a run. The plan tier is visible in `RunSummary.plan_tier` and routed calls in `RunSummary.routing`.
- **Reading the audit trail:** every action emits an `intervention.applied` event (with `action`, `policy_id`, `reason`, `human_review_required`); the run-explorer `--policy` flag surfaces them, and OTel export forwards them as span attributes.
- **Exporting traces to OTel backend:** `OtlpExporter(endpoint=...).export_events(events)` or `--otel` on the explorer.
