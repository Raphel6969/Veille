"""OpenTelemetry-compatible export interface (vendor wiring deferred to Phase 1)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from supervisor.contracts.events import RunEvent


@runtime_checkable
class OTelExporter(Protocol):
    """Export normalized supervisor events to an observability backend."""

    def export_events(self, events: list[RunEvent]) -> None:
        """Send events to the configured exporter."""
        ...


class NoOpOTelExporter:
    """Phase 0 default — accepts events without external export."""

    def __init__(self) -> None:
        self.exported: list[RunEvent] = []

    def export_events(self, events: list[RunEvent]) -> None:
        self.exported.extend(events)
