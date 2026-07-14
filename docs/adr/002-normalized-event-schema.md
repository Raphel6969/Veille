# ADR-002: Normalized Event Schema v0.1

## Status

Accepted — Phase 0

## Context

The Supervisor needs replayable, vendor-neutral run facts that support policy evaluation, cost aggregation, and observability export. Generic framework logs are insufficient for decision/intervention rationale.

## Decision

Define a versioned `RunEvent` model (`schema_version: 0.1.0`) with:

- Explicit `EventType` enum covering run, agent, model, tool, retry, policy, validation lifecycle
- OTel-aligned optional fields (`duration_ms`, token counts, `cost_usd`)
- Extensible `attributes` dict for hashes, previews, and policy metadata
- `RunEventBatch` wrapper for fixtures and replay

Events are **independent** of LangGraph, LiteLLM, and observability vendor schemas.

## Consequences

### Positive

- Contract tests enforce compatibility across phases
- Fixtures provide baseline data before live instrumentation
- Extension point for supervisor decision ledger in `attributes` / future event types

### Negative

- Mapping layer required for OTel GenAI conventions (Phase 1)
- Schema evolution requires version bumps and migration discipline

## Fields intentionally omitted from fixtures

- Full prompts and tool payloads (use `prompt_preview` and `normalized_input_hash`)
- PII and credentials

## Implementation

- `src/supervisor/contracts/events.py`
- Fixtures: `fixtures/traces/*.json`
