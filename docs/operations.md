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

Phase 0 does not require these services for tests or the demo workflow.

## Common commands

```powershell
pytest -v
ruff check src tests examples
ruff format src tests examples
mypy src/supervisor
python -m examples.cited_market_research.agent --scenario all --write-fixtures
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

Set `LOG_LEVEL` in `.env`. Phase 0 demo prints JSON summaries to stdout.

## Runbooks (Phase 1+)

- Enabling observe-mode policies
- Switching a policy to enforce (requires approval)
- Exporting traces to OTel backend
