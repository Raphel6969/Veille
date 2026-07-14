# Phase 1 — Observe and explain: Implementation Plan

**Status:** Proposed — awaiting approval. Do not begin until the Phase 1 approval gate is approved.

**Carried over from Phase 0:** Phase 0 is complete and verified (pytest 23 passed, ruff/mypy clean, fixtures committed, repo initialized with `master`/`dev`/`pre_dev` on `github.com/Raphel6969/Veille`). One bug was fixed during verification (run-summary fields were missing from `RunEventBatch.metadata`).

## Goal

Make an agent run **inspectable without changing its behavior**. A developer can run the demo (or any LangGraph agent wrapped by the SDK) and immediately see *why* a run was expensive, slow, or failed.

## Non-goals (explicitly excluded)

- No automatic routing, no context mutation/compression, no `warn`/`enforce` actions.
- No durable storage wiring (Postgres / Redis / MinIO stay scaffold-only; Phase 1 keeps state in-memory/local).
- No Next.js control-plane UI. A CLI explorer ships first; a minimal FastAPI endpoint is optional/stretch.

## User-visible outcome

Running the demo or any wrapped LangGraph graph yields:

1. An **automatically collected** normalized event stream (no manual `TraceCapture`).
2. A **run summary**: total cost, latency, token counts; per-model, per-tool, per-step, per-agent breakdowns; ordered timelines.
3. A **run-explorer CLI** to inspect any recorded run (live or from a fixture) and see policy flags.
4. **Observe-only policy flags** (e.g., duplicate tool call, retry storm) recorded but never acted on.
5. **OTel-compatible export** of the run (console/OTLP, no vendor lock-in, no external calls by default).

## Architecture and design decisions

### D1. SDK shape — `src/supervisor/sdk/`

A `Supervisor` / run controller wraps a LangGraph compiled graph:

- `Supervisor.observe(graph, task_contract)` returns an instrumented graph, **or**
- `with supervisor.run(task_contract) as run:` context manager around `graph.invoke(...)`.

Instrumentation uses **LangGraph callbacks** (`on_chain_*` for agents/steps, `on_tool_*` for tools, `on_llm_*` for model calls, `on_retry_*`) mapped to `RunEvent`s. This replaces the manual `TraceCapture` in `examples/cited_market_research/agent.py`.

> Decision to confirm: callback-based instrumentation (recommended) vs. wrapping `invoke`. Callbacks are the LangGraph-idiomatic path and survive graph structure changes.

### D2. Event collection — implement the LangGraph adapter port

`LangGraphAdapter.attach()` (port in `adapters/langgraph/port.py`) is implemented as `LangGraphInstrumentedAdapter` that registers a `LangGraphEventHook`. The hook converts callbacks → `RunEvent` and forwards to an in-memory `EventSink`. The Phase 0 stub is retired/renamed.

### D3. Aggregation — `src/supervisor/analytics/` (or `run_summary.py`)

Consumes a `RunEventBatch` → `RunSummary`: totals (cost, latency, tokens), counts (model / tool / retry / context), ordered timelines, and per-step / per-agent rollups. Pure and deterministic; fully unit-tested.

### D4. Context inventory / token accounting

The SDK emits `context.attached` events when context is supplied to a step. `RunSummary` accounts included/excluded/compressed tokens. The demo emits a **simple, role-aware context manifest** per agent (researcher / analyst / writer) — observe-only, no real compression logic (that is Phase 3).

### D5. Policy engine (observe-only) — `src/supervisor/policy/`

Implements evaluation of `PolicyDefinition`. For Phase 1 ship at least two observe-mode detectors:

- `duplicate_tool_protection` — same tool + `normalized_input_hash` seen twice → emits `policy.triggered` + `intervention.applied` (observe) but takes **no action**.
- `retry_budget` — `retry.scheduled` count exceeds a threshold → observe flag.

The engine is **mode-aware**: `warn`/`enforce` actions are feature-flagged off in Phase 1 (implemented in Phase 2). Hard rule: observe-mode evaluation must never alter execution. Unit tests prove non-interference against the `expensive` fixture.

### D6. Run explorer — `src/supervisor/cli.py`

`python -m supervisor.cli explore --run <fixture>` (and `--live` for the demo) prints the run summary, timeline, and policy flags. CLI is the primary deliverable. A minimal FastAPI `/runs/{id}` endpoint is optional/stretch and documented, not built unless approved.

> Decision to confirm: CLI-first (recommended). FastAPI only if a programmatic HTTP surface is needed for the showcase.

### D7. OTel export — `src/supervisor/telemetry/exporter.py`

Replace `NoOpOTelExporter` with a real `OTelExporter` mapping `RunEvent` → OTel spans/logs using GenAI semantic-convention attributes where applicable; export via console or OTLP. Vendor wiring deferred; exporter selection is config-driven with console as default (no external calls).

## Files / components expected to change

| Path | Change |
|---|---|
| `src/supervisor/sdk/` (new) | `controller.py`, `run_context.py`, `__init__.py` |
| `src/supervisor/adapters/langgraph/` | Implement `attach()` + callback hook; retire stub |
| `src/supervisor/analytics/` (new) | `run_summary.py` aggregation |
| `src/supervisor/policy/engine.py` (new) | Observe-only evaluation |
| `src/supervisor/telemetry/exporter.py` | Real `OTelExporter` mapping |
| `src/supervisor/cli.py` (new) | Run explorer |
| `examples/cited_market_research/agent.py` | Replace manual `TraceCapture` with SDK `observe`; emit `context.attached` |
| `tests/sdk/`, `tests/analytics/`, `tests/policy/`, `tests/telemetry/` (new) | New suites |
| `tests/examples/` | Update to use SDK instead of manual capture |

## Documentation deliverables (per master prompt)

- **ADR-004:** LangGraph instrumentation approach (callback-based).
- **ADR-005:** OTel export mapping (event → span/attribute convention).
- `docs/data-contracts.md`: add an **event `attributes` key registry** (canonical keys per event type: `normalized_input_hash`, `prompt_preview`, `duplicate`, `failed`, `call_count`, `attempt`, `role`, `scenario`, `checks`, …). This is the highest-value doc gap for Phase 1 instrumentation authors.
- `docs/architecture.md`, `docs/runtime-chain.md`: mark *Execute and Monitor* and *Observe-only policy* as implemented.
- `docs/policy-engine.md`: document the observe-only engine.
- `docs/integrations.md`: LangGraph adapter implemented; OTel exporter implemented.
- `docs/operations.md`: document the CLI explorer commands.
- `README.md`, `docs/roadmap.md`, `CHANGELOG.md`: update Phase 1 status after completion.
- (Optional, recommended) `CONTRIBUTING.md`: how to add a contract field / adapter / policy / test, regenerate fixtures, run checks.

## Tests and acceptance criteria

- **Contract:** event schema round-trip passes; new `context.attached` attributes documented and tested.
- **SDK auto-capture:** wrapping the demo graph auto-emits run / agent / model / tool / retry / context events; counts match expectation without manual capture.
- **Non-interference:** observe-mode policy evaluation yields the identical final brief vs. Phase 0 baseline (output unchanged).
- **Aggregation:** `RunSummary` totals equal sum of events; per-step/per-model breakdowns correct.
- **Observe policy:** duplicate-tool and retry-budget detectors flag the `expensive` fixture but emit no action.
- **OTel:** exporter emits spans for a batch with no external network; console exporter verified.
- **CLI:** `explore` on each fixture prints summary + flags.

**Master-prompt acceptance:**

- A representative run captures model, tool, context, retry, and timing events. ✓
- A developer can explain why a run was expensive, slow, or failed. ✓
- Observe-mode policy events do not change execution. ✓
- Trace/event schema contract tests pass. ✓

## Risks, assumptions, dependencies

- **LangGraph callback API stability** (assumption A-002) — pin version; keep adapter behind the port.
- **Token/cost derivation:** for the demo the LiteLLM mock supplies cost/tokens; for real LLMs, accurate cost mapping is refined later. Phase 1 still works with mock models (ADR-003).
- **Context accounting in the demo is illustrative** (simple role manifests); the real context engine is Phase 3.
- **Explorer surface:** CLI-first (recommended) vs. minimal FastAPI — confirm.
- **Instrumentation mechanism:** LangGraph callbacks (recommended) — confirm.

---

## Phase 1 approval gate

```
Phase 1 is ready to begin.

Goal: Make an agent run inspectable without changing its behavior.

Scope:
  - Python SDK + LangGraph adapter instrumentation (callback-based)
  - Automatic normalized event collection (replaces manual TraceCapture)
  - Token / cost / latency aggregation and run summary
  - Context inventory / token accounting (observe-only, illustrative manifests)
  - Observe-only policy evaluation (duplicate-tool, retry-budget) — never acts
  - Run-explorer CLI
  - OTel-compatible export mapping (console/OTLP, no vendor lock-in)

Not in scope:
  - warn / enforce actions, routing, context mutation/compression
  - durable storage (Postgres/Redis/MinIO) deep wiring
  - Next.js control-plane UI

Key decisions / assumptions:
  - LangGraph callback-based instrumentation
  - CLI-first explorer (FastAPI optional)
  - observe-only policies never alter execution
  - mock models default; no paid API calls

Validation:
  - pytest: SDK auto-capture, non-interference, aggregation,
    observe-policy, OTel, CLI explorer
  - ruff + mypy clean
  - demo runs without API keys on Python 3.14

Risks / questions:
  - LangGraph callback API changes (pinned; adapter behind port)
  - context accounting illustrative until Phase 3
  - confirm CLI-first vs FastAPI for explorer

May I implement Phase 1 now?
```
