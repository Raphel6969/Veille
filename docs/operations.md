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
- **Switching a policy to enforce (Phase 2):** requires explicit approval; not available in Phase 1.
- **Exporting traces to OTel backend:** `OtlpExporter(endpoint=...).export_events(events)` or `--otel` on the explorer.
