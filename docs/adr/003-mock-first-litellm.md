# ADR-003: Mock-First LiteLLM with Opt-In Real Providers

## Status

Accepted — Phase 0

## Context

The demo workflow, CI, and local development must run **without paid API credits**. The blueprint recommends LiteLLM for provider abstraction while keeping routing policy in the Supervisor.

## Decision

1. Implement `LiteLLMMockAdapter` as the **default** model access path.
2. Return deterministic token counts, costs, and latency for named mock models.
3. Real LiteLLM calls are opt-in via `USE_MOCK_MODELS=false` and the `litellm` optional extra.
4. Attempting real calls without configuration raises a clear error.

## Consequences

### Positive

- Reproducible demos and tests
- No accidental spend in CI or onboarding
- Pricing shape established before real provider metadata

### Negative

- Cost estimates in Phase 0 are illustrative, not provider-accurate
- Additional work in Phase 1 to wire real LiteLLM pricing

## Mock models

| Model | Role in demo |
|---|---|
| `mock-research` | Research and analysis steps |
| `mock-synthesis` | Brief writing |
| `mock-review` | Reserved for Phase 3 reviewer pass |

## Implementation

- `src/supervisor/adapters/litellm/mock.py`
- `.env.example`: `USE_MOCK_MODELS=true`
