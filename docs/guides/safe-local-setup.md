# Safe local setup (mock providers)

By default, Veille runs everything in **mock mode** — no API keys, no external HTTP calls, no costs. This is the safe default for local development and CI.

## How mock mode works

1. Every provider driver (`openai`, `anthropic`, `gemini`, etc.) returns mock completions with realistic token counts and costs.
2. Workflow tools are synthetic (no real API calls).
3. The cross-run cache is in-memory and never touches disk.
4. Policy rules are observed but never enforced.

## Verifying mock mode

```powershell
veille doctor
```

Expected output:

```
execution mode:      mock
policy mode:         observe (warn/enforce via SUPERVISOR_ENFORCE)
safe configuration warnings: none
```

## What you get

| Capability | Mock | Real |
|---|---|---|
| Model completions | Synthetic responses with token/cost metadata | Requires API key |
| Tool calls | Synthetic (no network) | Requires API endpoint |
| Cache | In-memory LRU (per-run) | In-memory or file-backed (opt-in) |
| Enforcement | Observe only | Requires `SUPERVISOR_ENFORCE=true` |
| Optimization | Recommend only | Serves from cache (opt-in) |
| Memory | Store/retrieve with mock records | Same (storage is always local) |

## Running in mock mode

```powershell
# No .env file needed — defaults are all mock
veille demo mock
veille run cited_market_research --input '{"scenario":"success"}'
```

## Switching to real mode

1. Copy `.env.example` to `.env`
2. Set `VEILLE_REAL_MODE=true`
3. Provide at least one API key (e.g. `OPENAI_API_KEY=sk-...`)
4. Run with `--yes` to confirm real execution

See [Real provider setup](real-provider-setup.md).
