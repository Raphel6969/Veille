# ADR-004: LangGraph instrumentation via callback handler

- **Status:** Accepted (Phase 1)
- **Date:** 2026-07-14

## Context

Phase 1 must capture agent lifecycle events automatically without the agent author
hand-writing `TraceCapture` calls. LangGraph exposes execution through a
`BaseCallbackHandler` that receives `on_llm_start/end`, `on_tool_start/end`, and graph
events. Two options were considered:

1. **Manual tracing** in the agent body (Phase 0 approach) — explicit but noisy and
   easy to forget.
2. **Callback-based instrumentation** wrapping the compiled graph — zero-touch capture
   once attached.

## Decision

Instrument LangGraph through a `LangGraphCallbackHandler` subclass attached to the
compiled graph by `LangGraphInstrumentedAdapter.attach(...)`. The adapter:

- Derives `run_id` from `config["configurable"]["thread_id"]` (falls back to a generated id).
- Emits `run.started`/`run.completed` around invocation.
- Converts LLM callbacks to `model.requested`/`model.completed` (with token usage).
- Converts tool callbacks to `tool.requested`/`tool.completed`, computing
  `normalized_input_hash` for duplicate detection.
- Returns an instrumented graph whose `.invoke`/`.stream` drive the handler.

The SDK (`Supervisor`) remains the single place that constructs `RunEvent`s, keeping
event schema ownership out of the adapter.

## Consequences

- Agent code only calls `adapter.attach(graph)` and `supervisor.finish_run(...)`.
- The demo no longer imports `TraceCapture` for event collection (it remains for
  input validation only).
- Future frameworks (e.g. CrewAI, custom loops) can implement the same adapter port.
