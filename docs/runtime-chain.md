# Runtime Chain

The Supervisor implements work around this conceptual chain. Phase 0 establishes contracts and a synthetic workflow; later phases add behavior at each stage.

```mermaid
flowchart TD
    A[Agent Request] --> B[Inspect Request]
    B --> C[Create / Select Execution Plan]
    C --> D[Estimate Cost and Latency]
    D --> E[Optimize and Diversify Context]
    E --> F[Route Model by Capability Fit]
    F --> G[Execute and Monitor]
    G --> H[Detect Problems and Drift]
    H --> I[Apply Safe Optimizations or Interventions]
    I --> J[Validate Outcome]
    J --> K[Return Response, Evidence, and Run Explanation]
```

## Stage reference

| Stage | Phase 0 | Inputs | Outputs | Failure paths |
|---|---|---|---|---|
| Agent Request | Demo only | User query, task contract YAML | Initial agent state | Missing contract |
| Inspect Request | **Planned Phase 3** | Task contract, request metadata | Intent classification | Unsupported task type |
| Create / Select Plan | Schema only | Task contract | `ExecutionPlan` skeleton | — |
| Estimate Cost/Latency | **Planned Phase 3** | Plan, model pricing | Tier options (Min/Balanced/High/Max) | Exceeds policy budget |
| Optimize Context | **Planned Phase 3** | Master context, step role | Context manifest | Conflict detected |
| Route Model | **Planned Phase 3** | Step capabilities, registry | Routing decision + reason | No approved model |
| Execute and Monitor | SDK + callbacks (Phase 1) | LangGraph graph, mock or live tools | `RunEvent` stream | Tool/model errors |
| Detect Problems | Observe mode (Phase 1) | Event stream | Policy triggers (`observe`) | — |
| Intervene | **Planned Phase 2** | Policy match | Intervention record | Unsafe to act |
| Validate Outcome | Demo validation | Brief artifact, task contract | `ValidationReport` | Checks fail |
| Return Result | Demo stdout | Report, events | JSON summary | Run failed |

## Phase 0 demo path

The cited market-research workflow exercises a subset of the chain:

1. Load task contract from YAML
2. Run LangGraph (instrumented via `LangGraphInstrumentedAdapter`): researcher → analyst → writer
3. Events captured automatically by the SDK/callback handler
4. Validate brief against quality checks (`validate_brief`)
5. Emit `validation.completed` and `run.completed` events

Embedded waste patterns (not blocked in Phase 0):

- **expensive scenario:** duplicate `search_competitors` call, retry storm on `fetch_source`
- **failed_validation scenario:** missing citations in synthesized brief

These patterns exist to support Phase 2 policy fixtures.

## Phase 1 detection (observe)

Phase 1 detects waste patterns from the event stream without changing execution:

- Duplicate tool calls via `normalized_input_hash` (only flags an equivalent *successful* prior call).
- Retry storms via `retry.attempt` against `RETRY_BUDGET` (default 5).
- Cost overruns via `total_cost_usd` vs `max_cost_usd`.
- Validation failures via `validation.completed`.

Each match emits a `policy.triggered` event with `policy_id`, `mode`, and `reason`. The recommended `intervention` field is advisory only—Phase 1 never acts.

## Decision ledger

Generic traces do not capture full supervisor policy rationale. `policy.triggered` events (Phase 1) carry `policy_id`/`mode`/`reason`; a structured decision/intervention record extends normalized events in Phase 2.
