"""OpenTelemetry-compatible export interface (Phase 1).

Maps normalized ``RunEvent`` facts to OTel-style span records using GenAI
semantic-convention attribute keys where applicable. No external OTel SDK is
required for the console exporter; an OTLP exporter is available lazily when the
``opentelemetry-sdk`` package is installed. Vendor wiring stays deferred.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from supervisor.contracts.events import EventType, RunEvent

_OPERATION_NAME: dict[EventType, str] = {
    EventType.RUN_STARTED: "agent.run",
    EventType.RUN_COMPLETED: "agent.run",
    EventType.AGENT_STARTED: "agent",
    EventType.AGENT_FINISHED: "agent",
    EventType.MODEL_REQUESTED: "chat",
    EventType.MODEL_COMPLETED: "chat",
    EventType.TOOL_REQUESTED: "execute_tool",
    EventType.TOOL_COMPLETED: "execute_tool",
    EventType.CONTEXT_ATTACHED: "context",
    EventType.MEMORY_RETRIEVED: "retrieve_memory",
    EventType.RETRY_SCHEDULED: "retry",
    EventType.RETRY_COMPLETED: "retry",
    EventType.POLICY_TRIGGERED: "policy",
    EventType.INTERVENTION_APPLIED: "policy",
    EventType.VALIDATION_COMPLETED: "validate",
}


@runtime_checkable
class OTelExporter(Protocol):
    """Export normalized supervisor events to an observability backend."""

    def export_events(self, events: list[RunEvent]) -> None: ...


def event_to_span(event: RunEvent) -> dict[str, Any]:
    """Convert a single ``RunEvent`` to an OTel-style span record."""
    start = event.timestamp
    end = start
    if event.duration_ms is not None:
        from datetime import timedelta

        end = start + timedelta(milliseconds=event.duration_ms)

    attributes: dict[str, Any] = {
        "gen_ai.operation.name": _OPERATION_NAME.get(event.event_type, "agent"),
        "supervisor.event_type": event.event_type.value,
        "supervisor.run_id": event.run_id,
    }
    if event.step_id is not None:
        attributes["supervisor.step_id"] = event.step_id
    if event.agent_id is not None:
        attributes["supervisor.agent_id"] = event.agent_id
    if event.model_name is not None:
        attributes["gen_ai.response.model"] = event.model_name
        attributes["gen_ai.request.model"] = event.model_name
    if event.tool_name is not None:
        attributes["tool.name"] = event.tool_name
    if event.input_tokens is not None:
        attributes["gen_ai.usage.input_tokens"] = event.input_tokens
    if event.output_tokens is not None:
        attributes["gen_ai.usage.output_tokens"] = event.output_tokens
    if event.cost_usd is not None:
        attributes["supervisor.cost_usd"] = event.cost_usd
    if event.status is not None:
        attributes["supervisor.status"] = event.status
    if event.error_message is not None:
        attributes["error.type"] = event.error_message
    for key, value in event.attributes.items():
        attributes[f"supervisor.attr.{key}"] = value

    return {
        "trace_id": event.run_id,
        "span_id": str(uuid4()),
        "name": event.event_type.value,
        "start_time": start.isoformat() if start is not None else None,
        "end_time": end.isoformat() if end is not None else None,
        "attributes": attributes,
    }


class ConsoleOTelExporter:
    """Phase 1 exporter: prints OTel-style span JSON to stdout."""

    def __init__(self) -> None:
        self.exported: list[dict[str, Any]] = []

    def export_events(self, events: list[RunEvent]) -> None:
        spans = [event_to_span(e) for e in events]
        self.exported.extend(spans)
        for span in spans:
            print(json.dumps(span, default=str))


class NoOpOTelExporter:
    """Fallback exporter that accepts events without external export."""

    def __init__(self) -> None:
        self.exported: list[RunEvent] = []

    def export_events(self, events: list[RunEvent]) -> None:
        self.exported.extend(events)


class OtlpExporter:
    """Lazy OTLP exporter; requires ``opentelemetry-sdk`` to be installed."""

    def __init__(self, endpoint: str = "http://localhost:4317") -> None:
        self.endpoint = endpoint
        self._spans: list[dict[str, Any]] = []
        self.exported: list[dict[str, Any]] = []

    def export_events(self, events: list[RunEvent]) -> None:
        spans = [event_to_span(e) for e in events]
        self._spans.extend(spans)
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.trace import Tracer

            provider = TracerProvider()
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=self.endpoint))
            )
            tracer: Tracer = provider.get_tracer("ai-runtime-supervisor")
            for span in spans:
                with tracer.start_as_current_span(span["name"]) as s:
                    s.set_attributes(
                        {
                            k: v
                            for k, v in span["attributes"].items()
                            if isinstance(v, (str, int, float, bool))
                        }
                    )
            self.exported.extend(spans)
        except Exception:
            # Defer to console if the OTel SDK is unavailable; never fail a run.
            console = ConsoleOTelExporter()
            console.export_events(events)
            self.exported.extend(console.exported)
