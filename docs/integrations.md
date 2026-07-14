# Integrations

Integration-first design: retain customer frameworks and connect via adapter ports.

## LangGraph adapter

**Status:** Port defined; stub implementation in Phase 0. Full instrumentation in Phase 1.

| Hook | Purpose |
|---|---|
| `on_run_started` / `on_run_finished` | Run lifecycle |
| `on_agent_event` | Agent step events |
| `on_tool_event` | Tool call events with normalized input hash |
| `on_model_event` | Model call events with token usage |
| `flush` | Return collected `RunEvent` list |

```python
# src/supervisor/adapters/langgraph/port.py
class LangGraphAdapter(Protocol):
    def attach(self, graph: Any, hook: LangGraphEventHook) -> Any: ...
    def extract_run_id(self, config: dict[str, Any] | None) -> str: ...
```

Phase 0 stub returns the graph unchanged.

## LiteLLM adapter

**Status:** Mock adapter implemented. Real LiteLLM wiring opt-in via `litellm` extra.

| Method | Purpose |
|---|---|
| `complete(model, prompt)` | Return `MockCompletionResult` with tokens and cost |

Default models in demo: `mock-research`, `mock-synthesis`, `mock-review`.

Set `USE_MOCK_MODELS=false` and provide API keys to use real providers (Phase 1+).

## OpenTelemetry export

**Status:** Interface defined; vendor wiring deferred.

```python
class OTelExporter(Protocol):
    def export_events(self, events: list[RunEvent]) -> None: ...
```

`NoOpOTelExporter` collects events in-memory for tests. Phase 1 will map `RunEvent` fields to OTel GenAI semantic conventions.

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
