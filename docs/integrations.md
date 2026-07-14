# Integrations

Integration-first design: retain customer frameworks and connect via adapter ports.

## LangGraph adapter

**Status:** Implemented (Phase 1). Callback-based instrumentation via a LangGraph `BaseCallbackHandler`.

| Hook | Purpose |
|---|---|
| `on_run_started` / `on_run_finished` | Run lifecycle (derive run id from `config["configurable"]["thread_id"]`) |
| `on_agent_event` | Agent step events |
| `on_tool_event` | Tool call events with normalized input hash |
| `on_model_event` | Model call events with token usage |
| `flush` | Return collected `RunEvent` list |

```python
from supervisor.adapters.langgraph.adapter import LangGraphInstrumentedAdapter
from supervisor.sdk import Supervisor

supervisor = Supervisor(run_id="run-1", task_id="cited-competitor-brief-001")
adapter = LangGraphInstrumentedAdapter(supervisor)
app = adapter.attach(graph)
app.invoke(inputs, config={"configurable": {"thread_id": "run-1"}})
batch = supervisor.finish_run(task_contract_met=True)
```

The adapter attaches a `LangGraphCallbackHandler` so the agent emits normalized events with no manual `TraceCapture` wiring. See [ADR-004](adr/004-langgraph-callback-instrumentation.md).

## LiteLLM adapter

**Status:** Mock adapter implemented. Real LiteLLM wiring opt-in via `litellm` extra.

| Method | Purpose |
|---|---|
| `complete(model, prompt)` | Return `MockCompletionResult` with tokens and cost |

Default models in demo: `mock-research`, `mock-synthesis`, `mock-review`.

Set `USE_MOCK_MODELS=false` and provide API keys to use real providers (Phase 1+).

## OpenTelemetry export

**Status:** Implemented (Phase 1). `ConsoleOTelExporter` prints spans; `OtlpExporter` exports via OTLP/gRPC.

```python
from supervisor.telemetry import ConsoleOTelExporter, OtlpExporter

ConsoleOTelExporter().export_events(events)            # human-readable spans
OtlpExporter(endpoint="http://localhost:4317").export_events(events)
```

`event_to_span(event)` maps each `RunEvent` to an OTel span following the GenAI semantic conventions (span name = `event_type`, span kind = CLIENT for tool/model, attributes carry `run_id`, `agent_id`, `tool_name`, `model`, `cost_usd`, `duration_ms`, and the event `attributes` object). See [ADR-005](adr/005-otel-mapping.md).

## Deferred integrations

| System | Phase | Notes |
|---|---|---|
| Langfuse / Phoenix / LangSmith | 1+ | Export via OTel |
| Mem0 / Letta | 5+ | Memory connectors |
| Portkey | 3+ | Alternative gateway |
| Patronus / custom evaluators | 3+ | Evaluator connector |

## Adding a new adapter

1. Define a port (Protocol) in `src/supervisor/adapters/`
2. Document the contract in this file
3. Add an ADR for material integration choices
4. Add contract tests before implementation
