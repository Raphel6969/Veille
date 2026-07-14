from supervisor.contracts.events import EventType, RunEvent
from supervisor.telemetry import ConsoleOTelExporter, event_to_span


def test_event_to_span_maps_model() -> None:
    e = RunEvent(
        event_id="1",
        run_id="r",
        event_type=EventType.MODEL_COMPLETED,
        model_name="m",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.05,
        attributes={"prompt_preview": "x"},
    )
    span = event_to_span(e)
    assert span["name"] == "model.completed"
    assert span["attributes"]["gen_ai.response.model"] == "m"
    assert span["attributes"]["gen_ai.usage.input_tokens"] == 10
    assert span["attributes"]["gen_ai.operation.name"] == "chat"


def test_console_exporter_no_external() -> None:
    exporter = ConsoleOTelExporter()
    exporter.export_events([RunEvent(event_id="1", run_id="r", event_type=EventType.RUN_STARTED)])
    assert len(exporter.exported) == 1
