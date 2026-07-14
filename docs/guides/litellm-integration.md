# LiteLLM integration

LiteLLM is the default real-provider backend for Veille. When mock mode is off and a provider key is available, all completion calls route through `litellm.completion()`.

## How it works

1. Every `BaseModelProvider` subclass has a `_real()` method that calls `litellm.completion(model, messages, max_tokens, api_base, api_key)`.
2. The provider's `api_key_env` field determines which environment variable to read.
3. LiteLLM translates the unified call to the appropriate provider (OpenAI, Anthropic, Gemini, etc.) based on the model name.

## Provider configuration

| Provider | LiteLLM model prefix | Required env var |
|---|---|---|
| OpenAI | `gpt-4o`, `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-3.5-sonnet`, `claude-opus` | `ANTHROPIC_API_KEY` |
| Gemini | `gemini-1.5-pro`, `gemini-1.5-flash` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter/...` | `OPENROUTER_API_KEY` |
| Ollama | `ollama/llama3` | none (local) |
| LM Studio | `lmstudio/local-model` | none (local) |

## Using LiteLLM directly

```python
from supervisor.adapters.providers import get_provider

provider = get_provider("litellm")
result = provider.complete(
    model="gpt-4o",
    prompt="What is the capital of France?",
    max_output_tokens=100,
)
print(result.content)
```

## Environment

```ini
# .env
VEILLE_REAL_MODE=true
OPENAI_API_KEY=sk-...
LITELLM_MODEL=gpt-4o-mini
```

## Safety

- LiteLLM is imported lazily (inside `_real()`). If missing, the provider raises a clear error asking you to `pip install litellm`.
- LiteLLM never stores or logs API keys — they are passed directly to each provider.
- The console always masks keys before any output.
