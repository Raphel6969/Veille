# Architecture

## Overview

The AI Runtime Supervisor is a **control plane** that sits between agent applications and model/tool providers. It does not replace agent frameworks, gateways, or observability platforms—it integrates with them.

```mermaid
flowchart TB
    subgraph app [Agent Application]
        Framework[LangGraph agent]
    end
    subgraph supervisor [AI Runtime Supervisor — Phase 0 scope]
        Contracts[Data contracts]
        Adapters[Adapter ports]
        Demo[Synthetic demo workflow]
        Fixtures[Trace fixtures]
    end
    subgraph future [Phase 1+ — planned]
        SDK[Python SDK]
        RunController[Run controller]
        PolicyEngine[Policy engine]
        ContextEngine[Context engine]
        RoutingEngine[Routing engine]
    end
    subgraph infra [Infrastructure scaffold]
        Postgres[(PostgreSQL)]
        Redis[(Redis)]
        MinIO[(MinIO)]
    end
    Framework --> Demo
    Demo --> Contracts
    Demo --> Fixtures
    Adapters -.-> SDK
    SDK -.-> RunController
    RunController -.-> PolicyEngine
    RunController -.-> ContextEngine
    RunController -.-> RoutingEngine
    RunController -.-> Postgres
    RunController -.-> Redis
    RunController -.-> MinIO
```

## Phase 0 components

| Component | Path | Status |
|---|---|---|
| Task contract models | `src/supervisor/contracts/task.py` | Implemented (v0.1) |
| Run event models | `src/supervisor/contracts/events.py` | Implemented (v0.1) |
| Execution plan skeleton | `src/supervisor/contracts/plan.py` | Schema only |
| Policy definition skeleton | `src/supervisor/contracts/policy.py` | Schema only |
| Validation report | `src/supervisor/contracts/validation.py` | Implemented (v0.1) |
| LiteLLM mock adapter | `src/supervisor/adapters/litellm/mock.py` | Implemented |
| Demo workflow | `examples/cited_market_research/` | Implemented |
| Trace fixtures | `fixtures/traces/` | Implemented |

## Phase 1 components (Observe and explain)

| Component | Path | Status |
|---|---|---|
| Python SDK (`Supervisor` + `RunCollector`) | `src/supervisor/sdk/` | Implemented (v0.1) |
| LangGraph adapter (callback-based) | `src/supervisor/adapters/langgraph/adapter.py` | Implemented |
| Run summary analytics | `src/supervisor/analytics/run_summary.py` | Implemented |
| Observe-only policy engine | `src/supervisor/policy/engine.py` | Implemented (observe mode) |
| OTel exporter (Console + OTLP) | `src/supervisor/telemetry/exporter.py` | Implemented |
| Run-explorer CLI | `src/supervisor/cli.py` | Implemented |
| Demo refactored to use SDK | `examples/cited_market_research/agent.py` | Implemented |

## Phase 3 components (Advisory planning, context, routing)

| Component | Path | Status |
|---|---|---|
| Planner (tier selection + plan) | `src/supervisor/planning/planner.py` | Implemented |
| Context engine (per-step manifests) | `src/supervisor/context/engine.py` | Implemented |
| Model routing (capability + tier) | `src/supervisor/routing/router.py` | Implemented |
| SDK `plan` / `route_model` / `context(master_context=)` | `src/supervisor/sdk/supervisor.py` | Implemented |
| Run summary `plan_tier` + `routing` | `src/supervisor/analytics/run_summary.py` | Implemented |
| Demo wired with `SUPERVISOR_PLAN=1` opt-in | `examples/cited_market_research/agent.py` | Implemented |

## Data boundaries

- **Contracts are vendor-neutral.** Event and task schemas do not depend on LangGraph, LiteLLM, or any observability vendor.
- **Safe metadata by default.** Raw prompts and tool payloads are not persisted in fixtures; only previews and hashes.
- **Mock-first execution.** Demo and tests run without paid API credits unless explicitly opted in.

## Integration points

| Port | Phase | Purpose | Status |
|---|---|---|---|
| LangGraph adapter | 1 | Capture framework lifecycle events | Implemented (callback handler) |
| LiteLLM adapter | 1+ | Model access with pricing metadata | Mock implemented |
| OTel exporter | 1 | Portable telemetry export | Implemented (Console + OTLP) |
| Postgres store | 1+ | Run metadata and audit | Scaffold only |
| Redis counters | 2+ | Budgets and rate windows | Planned |

## Architecture rules

1. Keep public contracts independent of any gateway, framework, or observability vendor.
2. Implement integrations behind explicit adapter ports.
3. Feature-flag each policy, router, and enforcement action (Phase 2+).
4. Use safe metadata and redaction by default.
5. Begin all policies in observe mode.

## Related documents

- [Runtime chain](runtime-chain.md)
- [Data contracts](data-contracts.md)
- [Integrations](integrations.md)
- [ADRs](adr/)
