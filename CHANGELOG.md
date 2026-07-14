# Changelog

All notable changes are documented here. This project follows phase-based delivery.

## [Unreleased]

### Phase 1 — Observe and explain (implemented, pending release)

- **Python SDK** (`src/supervisor/sdk/`): `Supervisor` emission helpers
  (`start_run`, `finish_run`, `model`, `tool`, `retry`, `context`, `node`,
  `emit_validation`) and `RunCollector` aggregation.
- **LangGraph adapter** (`src/supervisor/adapters/langgraph/adapter.py`): callback-based
  automatic instrumentation; agent authors call `adapter.attach(graph)` only.
- **Run summary analytics** (`src/supervisor/analytics/run_summary.py`): `summarize()`
  produces a `RunSummary` (tool call counts, duplicates, retries, cost, timeline,
  policy observations, validation result).
- **Observe-only policy engine** (`src/supervisor/policy/engine.py`): `evaluate_observe`
  detects duplicate tool calls, retry storms (budget 5), cost overruns, and validation
  failures; emits `policy.triggered` events. Never alters execution.
- **OTel exporter** (`src/supervisor/telemetry/exporter.py`): `ConsoleOTelExporter`
  (default) and `OtlpExporter` (OTLP/gRPC) via `event_to_span`.
- **Run-explorer CLI** (`src/supervisor/cli.py`): `explore` subcommand for fixtures
  (`--run`) or live runs (`--live --scenario`) with `--policy` and `--otel` flags.
- **Demo refactor** (`examples/cited_market_research/agent.py`): now uses the SDK;
  `trace_capture.py` reduced to `validate_brief` input validation only.
- **Tests:** sdk, analytics, policy, telemetry mapping, langgraph adapter, cli, and
  demo smoke — 39 tests passing.
- **Docs:** ADR-004 (LangGraph callbacks), ADR-005 (OTel mapping), event attributes
  registry in `data-contracts.md`, updated architecture/runtime-chain/policy-engine/
  integrations/operations/roadmap.
- **Quality gates:** `ruff`, `mypy --strict`, `pytest` all green on Python 3.14.

## [0.1.0] — Phase 0 baseline (2026-07-14)

- Data contracts v0.1: task contract, run events, validation report.
- Adapter ports: LangGraph (interface), LiteLLM mock, OTel interface.
- Synthetic cited market-research LangGraph workflow.
- Trace fixtures (success, expensive, failed_validation).
- Documentation system, docker compose, CI, dev scripts.
