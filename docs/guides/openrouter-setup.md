# OpenRouter integration

OpenRouter provides a unified API for dozens of model providers. Veille supports it as a first-class provider driver.

## Setup

```powershell
$env:OPENROUTER_API_KEY="sk-or-..."
$env:VEILLE_REAL_MODE="true"
```

## Usage

```powershell
# Verify connection
veille connections validate openrouter

# Run a workflow via OpenRouter
veille run cited_market_research --input '{"scenario":"success"}' --yes
```

The console derives the `openrouter` provider from model names starting with `openrouter/`:

- `openrouter/gpt-4o`
- `openrouter/claude-3.5-sonnet`
- `openrouter/gemini-1.5-pro`

## Model routing

When you set `VEILLE_PROVIDER=openrouter`, the router selects models from the OpenRouter candidate list. The console automatically sets `provider="openrouter"` on every model event.

## Confirmation

OpenRouter is a paid proxy. The console always requires `--yes` before executing real model calls through any provider, including OpenRouter.
