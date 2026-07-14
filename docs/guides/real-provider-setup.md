# Real provider setup

To run workflows against real model providers instead of mocks:

## 1. Configure credentials

Copy `.env.example` to `.env` and set:

```ini
VEILLE_REAL_MODE=true

# At least one provider key:
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=...
# OPENROUTER_API_KEY=...
```

## 2. Verify the connection

```powershell
veille connections validate openai
```

Expected:

```
OK openai: Credential found.
```

## 3. Run a workflow in real mode

```powershell
veille run cited_market_research --input '{"scenario":"success"}' --yes
```

The `--yes` flag confirms you want real execution. Without it, the console prints a warning and stays in mock mode.

## 4. Run the real-world demo

The `real_world_demo` workflow uses a read-only HTTP API. No API key is needed for the data source, but model calls still go through a provider:

```powershell
veille demo real-world --yes
```

## Switching providers

Set the provider via environment variable:

```powershell
$env:VEILLE_PROVIDER="anthropic"
$env:VEILLE_MODEL="claude-3.5-sonnet"
veille run cited_market_research --input '{"scenario":"success"}' --yes
```

Or pass inline:

```powershell
$env:VEILLE_REAL_MODE="true"
$env:ANTHROPIC_API_KEY="sk-ant-..."
veille run cited_market_research --input '{"scenario":"success"}' --yes
```

## Supported providers

| Provider | Env var | Model example |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3.5-sonnet` |
| Gemini | `GEMINI_API_KEY` | `gemini-1.5-pro` |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/gpt-4o` |
| Ollama | `OLLAMA_BASE_URL` | `ollama/llama3` |
| LM Studio | `LMSTUDIO_BASE_URL` | `lmstudio/local-model` |
| LiteLLM | `OPENAI_API_KEY` + `LITELLM_MODEL` | `litellm/gpt-4o` |

## Safety

- Real mode is **not** required. The console defaults to mock and only switches when `VEILLE_REAL_MODE=true` is set.
- Confirmation (`--yes`) is required once per session per real execution.
- API keys are never printed, stored, or returned by any console command.
