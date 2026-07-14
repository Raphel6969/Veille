from datetime import UTC, datetime

from supervisor.contracts.events import EventType, RunEvent
from supervisor.telemetry.exporter import NoOpOTelExporter


def test_noop_exporter_collects_events() -> None:
    exporter = NoOpOTelExporter()
    events = [
        RunEvent(
            event_id="e1",
            run_id="r1",
            event_type=EventType.RUN_STARTED,
            timestamp=datetime.now(UTC),
        )
    ]
    exporter.export_events(events)
    assert len(exporter.exported) == 1
