# Integrations

Integration-first design: retain customer frameworks and connect via adapter ports.

## Adapter ports

All adapters implement `FrameworkAdapter` (a Protocol from `src/supervisor/adapters/ports.py`). The console discovers installed adapters at runtime.

| Adapter | Status | Package |
|---|---|---|
| LangGraph | **Implemented** (Phase 1) | `langgraph` (dev dependency) |
| OpenAI Agents SDK | **Skeleton** | `openai-agents` (optional) |
| OpenAI Responses API | **Skeleton** | `openai` (optional) |
| Generic (any callable) | **Implemented** | none required |

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

## Model provider drivers

The console registers 8 provider drivers via `src/supervisor/adapters/providers/__init__.py`. Each extends `BaseModelProvider`.

| Provider | Identifier | API Key Env Var | Status |
|---|---|---|---|
| LiteLLM | `litellm` | `OPENAI_API_KEY` | Implemented |
| OpenAI | `openai` | `OPENAI_API_KEY` | Implemented |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | Implemented |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | Implemented |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | Implemented |
| Ollama | `ollama` | `OLLAMA_BASE_URL` | Implemented |
| LM Studio | `lmstudio` | `LMSTUDIO_BASE_URL` | Implemented |
| OpenAI-compatible | `openai-compatible` | `OPENAI_COMPATIBLE_API_KEY` | Implemented |

All providers default to **mock mode** — no credentials needed. Set `VEILLE_REAL_MODE=true` and supply the corresponding key to use real inference.

The `_derive_provider(model)` helper maps model strings to provider identifiers:

- `gpt-4o` → `openai`
- `openrouter/gpt-4o` → `openrouter`
- `claude-3.5-sonnet` → `anthropic`
- `gemini-1.5-pro` → `gemini`
- `ollama/llama3` → `ollama`
- `lmstudio/local-model` → `lmstudio`
- `litellm/gpt-4o` → `litellm`

## Generic framework adapter

**Status:** Implemented. Wraps any callable into an `InstrumentedAgent` that emits normalized events through the Supervisor SDK.

```python
from supervisor.adapters.generic import GenericFrameworkAdapter

adapter = GenericFrameworkAdapter()
agent = adapter.attach(my_callable, supervisor)
result = agent.run(input_data, config)
```

## OpenAI Agents SDK adapter

**Status:** Skeleton. When the `openai-agents` package is installed, routes through the native `Runner` so tracing integrates. Falls back to the generic adapter otherwise.

```python
from supervisor.adapters.openai_agents import OpenAIAgentsAdapter

adapter = OpenAIAgentsAdapter()
agent = adapter.attach(my_agent, supervisor)
```

## OpenAI Responses API adapter

**Status:** Skeleton. When the `openai` SDK is available, uses `client.responses.create` for native tracing. Falls back to the generic adapter otherwise.

```python
from supervisor.adapters.openai_responses import OpenAIResponsesAdapter

adapter = OpenAIResponsesAdapter()
agent = adapter.attach(my_agent, supervisor)
```

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
- `CachePolicy` (`src/supervisor/optimize/policy.py`): partner-validated rules — serve only identical normalized inputs (exact), composite keys include tenant/project/tool+policy version/auth+context boundaries, 300s TTL with re-execute on expiry/uncertainty, and a partner-confirmation rollout gate (`approved`). See [ADR-012](adr/012-cache-policy.md).
- `Supervisor.tool(..., idempotent=True)` / `Supervisor.model(..., cacheable=True)` consult `DuplicateDetector` and the cache; dry-run recommends, active serves allowlisted exact hits once the confirmation gate is met.

See [ADR-010](adr/010-semantic-dedup-caching.md).

## Memory governance (Phase 5, opt-in)

**Status:** Implemented (Phase 5). Gated behind `SUPERVISOR_MEMORY=1` (default off). The supervisor governs *memory inclusion*, not storage.

- `MemoryBackend` port (`src/supervisor/memory/store.py`): `InMemoryMemoryStore` is the default (no external deps, tenant-isolated). Mem0/Letta/customer RAG attach behind this port.
- `MemoryGovernor.retrieve(...)` scores candidates (recency/usage/provenance/confidence + role weights), flags `stale`/`drift`, and emits a `memory.retrieved` manifest. No automatic deletion — expiry is audited.
- `Supervisor.remember` / `retrieve_memory` / `expire_memory` / `forget_memory` are the SDK surface; off-mode `retrieve_memory` is a no-op passthrough.

```python
from supervisor.sdk import Supervisor

supervisor = Supervisor(task)
supervisor.remember(content="Prior query context", tier="long", role="researcher")
memories = supervisor.retrieve_memory(step_id="research", role="researcher", query="AI runtime supervision")
```

See [ADR-011](adr/011-memory-governance.md).

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
| Mem0 / Letta | 5+ (backend) | Memory connectors behind `MemoryBackend` port |
| Portkey | 3+ | Alternative gateway |
| Patronus / custom evaluators | 3+ | Evaluator connector |

## Adding a new adapter

1. Define a port (Protocol) in `src/supervisor/adapters/`
2. Document the contract in this file
3. Add an ADR for material integration choices
4. Add contract tests before implementation
