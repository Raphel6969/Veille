# ADR-013: Local Integration Console (Developer Edition)

- **Status:** Implemented (v0.2.0)
- **Date:** 2026-07-14

## Context

The runtime phases 1–5 and the cross-run cache are fully implemented but require developers to:
- Know the `SUPERVISOR_*` env-var names and opt-in flags
- Run workflows by invoking Python modules directly (`python -m examples.…`)
- Inspect results via the CLI run-explorer or raw trace JSON files
- Manually configure providers with no discoverability

The design-partner program confirmed that adoption increases when there is a **local integration console** — a developer CLI + web UI that registers workflows, connects model providers, runs real workflows through the supervisor runtime, and displays execution, planning, context, policies, interventions, traces, cache reuse, token usage, and validation — all without bypassing the runtime's safety rules.

## Decision

Build a Local Integration Console with three layers:

1. **Console backend** (`src/supervisor/console/`) — Python modules that reuse the existing analytics, planning, cache, and SDK surface instead of re-implementing it. Adds the VEILLE_* env-var namespace for console config (runtime opt-in stays on SUPERVISOR_*).

2. **CLI entry point** (`veille`) — single command that bundles doctor, connections, workflows, run, runs, providers, adapters, demo, explore, and serve subcommands. Registered as `[project.scripts] veille = "supervisor.cli:main"` in pyproject.toml.

3. **React+TypeScript+Vite web UI** (`ui/`) — six pages (Overview, Workflows, Run Explorer, Connections, Adapters, Policies) consuming the FastAPI server's REST endpoints.

### Safety rules (mandatory, hard-coded)

1. Never expose, print, commit, return, or store secrets. Credentials are always masked (`…abcd`) in every response body.
2. Require confirmation (`--yes`) before paid API calls, enabling enforcement, enabling optimization, enabling cross-run cache, or making persistent credential changes.
3. Default to **mock** providers, **mock** workflows, and **mock** tools. The console never fails at startup when credentials are missing — it shows guidance and continues in mock mode.
4. No second runtime. Every workflow execution goes through the `Supervisor` SDK, which enforces all opt-in checks, policy rules, and cache gates.
5. Provider port (`BaseModelProvider`) defaults to mock mode; real provider calls require explicitly setting `VEILLE_REAL_MODE=true` and providing a key.

### Provider drivers

The console registers 8 provider drivers via a single port:

- `LiteLLMProvider` — delegates to litellm for multi-provider inference
- `OpenAIProvider` — OpenAI API
- `AnthropicProvider` — Anthropic API
- `GeminiProvider` — Google Gemini API
- `OpenRouterProvider` — OpenRouter proxy
- `OllamaProvider` — local Ollama instance
- `LMStudioProvider` — local LM Studio instance
- `OpenAICompatibleProvider` — any OpenAI-compatible endpoint

All default to mock; real mode is gated behind `VEILLE_REAL_MODE=true` + the corresponding API key.

### Framework adapters

Adapters implement `FrameworkAdapter` (a Protocol in `src/supervisor/adapters/ports.py`):

| Adapter | Status |
|---|---|
| LangGraph (callback-based) | Implemented |
| OpenAI Agents SDK | Skeleton |
| OpenAI Responses API | Skeleton |
| Generic (any callable) | Implemented |

### Added event attributes (schema 0.2.0, additive)

- `model()` and `tool()` events carry optional `provider`, `prompt_version`, and `reuse_reason` attributes.
- `RoutingDecision` carries a `provider` field so the console can attribute model calls to their provider.

### Added routing changes

- `Router._default()` seeds both **mock** candidates (`mock-research`, etc.) and **real** candidates (`gpt-4o`, `openrouter/gpt-4o`, `claude-3.5-sonnet`, `gemini-1.5-pro`, `ollama/llama3`, `lmstudio/local-model`). The real candidates are ignored in mock mode.
- `Router.select()` sets `RoutingDecision.provider` via `_derive_provider(model)`.

### Cross-run cache

The cross-run (durable) cache from ADR-012 remains unchanged: opt-in, confirmation-gated, exact-input-only.

### CLI commands

| Command | Purpose |
|---|---|
| `veille doctor` | Report Python version, runtime version, installed adapters, registered workflows/providers/models, execution mode, policy mode, safe-config warnings |
| `veille connections [list\|validate <provider>]` | List provider connections or validate a specific one |
| `veille workflows [list\|inspect <name>]` | List registered workflows or inspect a specific one |
| `veille run <workflow> --input <json>` | Execute a registered workflow through the runtime |
| `veille runs [list\|show <id>]` | List saved runs or show detail |
| `veille providers list` | List registered provider drivers |
| `veille adapters list` | List installed framework adapters |
| `veille demo {mock,real-world}` | Run built-in demos |
| `veille explore --run <path>` | Inspect a trace fixture |
| `veille serve` | Start the FastAPI web server |

### Web UI pages

| Page | Endpoint | Display |
|---|---|---|
| Overview | `/api/doctor` | Python/runtime version, mode, cache, warnings |
| Workflows | `/api/workflows` | List workflows, run a workflow, show result |
| Run Explorer | `/api/runs` / `/api/runs/{id}` | List saved runs, select for detail |
| Connections | `/api/connections` + validate | Provider status, env var, masked key, validate |
| Adapters | `/api/adapters` | Installed adapters with name/status/description |
| Policies | `/api/doctor` | Policy mode, enforce/optimize/cache flags |

## Consequences

**Positive:**
- Developers can discover, configure, and run workflows without reading source code or env-var documentation.
- All provider connections are visible from one place.
- Runs are inspectable through a unified explorer (CLI and web).
- No secret is ever leaked — the masking and confirmation gates are enforced at the console layer, not just documented.
- The existing runtime is untouched; the console is a read-mostly shell over the SDK and analytics.

**Negative:**
- Adds ~3,000 lines of new code (console backend + CLI + web UI).
- The React UI is a build artifact that requires Node.js to develop or deploy.
- Provider drivers are hard-coded; adding a new provider requires a code change.

**Neutral:**
- The VEILLE_* variable namespace sits alongside SUPERVISOR_* — no migration needed for existing opt-in settings.
- The console is uncommitted (not pushed to PyPI); it lives on the `pre_dev` branch until the next release.

## Related

- [Architecture](architecture.md) — system overview with console layer
- [Operations](operations.md) — CLI commands and runbooks
- [Integrations](integrations.md) — adapter contracts and provider drivers
- [ADR-004](adr/004-langgraph-callback-instrumentation.md) — LangGraph adapter
- [ADR-008](adr/008-plan-tier-cost-model.md) — planning
- [ADR-009](adr/009-model-routing.md) — model routing
- [ADR-012](adr/012-cache-policy.md) — cache policy
