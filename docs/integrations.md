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

## Planning and routing (Phase 3, advisory)

**Status:** Implemented (Phase 3). Gated behind `SUPERVISOR_PLAN=1` (mirroring `SUPERVISOR_ENFORCE`). Does not block execution—annotates events only.

```python
from supervisor.sdk import Supervisor

supervisor = Supervisor(task)          # task = TaskContract
plan = supervisor.plan()                # selects PlanTier, builds ExecutionPlan
supervisor.start_run()

decision = supervisor.route_model(
    step_id="research", agent_id="researcher", capability="research"
)                                       # RoutingDecision (tier-aware)
supervisor.model(
    step_id="research", agent_id="researcher",
    model=decision.model, prompt="...",
    adapter=adapter, routing=decision,  # records routing_tier on model.requested
)
supervisor.context(
    step_id="research", agent_id="researcher", role="researcher",
    master_context=MASTER_CONTEXT,      # builds a ContextManifest via ContextEngine
)
```

The `ModelRegistry` is seeded with mock candidates (`mock-research`, `mock-analysis`, `mock-synthesis`, `mock-review`). Replace the registry to route to real providers without changing call sites. See [ADR-008](adr/008-plan-tier-cost-model.md) and [ADR-009](adr/009-model-routing.md).

## Optimization (Phase 4, opt-in)

**Status:** Implemented (Phase 4). Gated behind `SUPERVISOR_OPTIMIZE=1` (default sub-mode `dry_run`; `SUPERVISOR_OPTIMIZE_MODE=active` to serve from cache). Never changes execution unless explicitly activated.

- `SemanticKey` port (`src/supervisor/optimize/keys.py`): `ShingleSemanticKey` tokenizes input into word-shingles and compares with Jaccard similarity (default threshold 0.85). An embedding backend is a future port behind this interface.
- `CacheBackend` port (`src/supervisor/optimize/cache.py`): `InMemoryCache` (bounded LRU-ish FIFO + per-entry TTL) is the default; Redis is a later backend behind the same port.
- `Supervisor.tool(..., idempotent=True)` / `Supervisor.model(..., cacheable=True)` consult `DuplicateDetector` and the cache; dry-run recommends, active serves idempotent hits.

See [ADR-010](adr/010-semantic-dedup-caching.md).

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
