# ADR-005: OpenTelemetry event-to-span mapping

- **Status:** Accepted (Phase 1)
- **Date:** 2026-07-14

## Context

Observability platforms (Langfuse, Phoenix, LangSmith, Grafana) consume OpenTelemetry.
`RunEvent` is supervisor-internal and must be portable. We need a deterministic mapping
so exported spans carry the same semantics regardless of backend.

## Decision

Map each `RunEvent` to one OTel span via `event_to_span(event)`:

- **Span name:** `event_type` (e.g. `tool.completed`).
- **Span kind:** `CLIENT` for `tool.*` and `model.*` (external calls); `INTERNAL` otherwise.
- **Start/end time:** from `timestamp` (+ `duration_ms`).
- **Attributes:**
  - Core identity: `run_id`, `event_id`, `step_id`, `agent_id`, `tool_name`, `model`.
  - Telemetry: `cost_usd`, `duration_ms`, `status`, `error_message`.
  - All keys from the event `attributes` object are forwarded as-is (e.g.
    `normalized_input_hash`, `duplicate`, `retry.attempt`).

Two exporters implement `OTelExporter`:

- `ConsoleOTelExporter` — pretty-prints spans (default, no OTel SDK required).
- `OtlpExporter` — sends spans over OTLP/gRPC using the installed `opentelemetry`
  SDK (optional; only needed when `--otel` is used).

## Consequences

- Event schema changes propagate to spans automatically (attributes are forwarded).
- No backend-specific code in the supervisor core; only the exporter depends on the
  OTel SDK.
- Mapping follows GenAI semantic-convention intent; exact attribute names may be
  aligned further in Phase 2.
