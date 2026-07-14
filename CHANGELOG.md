# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2026-07-14

### Added — Phase 0 Foundation

- Repository scaffold: `pyproject.toml`, Docker Compose, CI workflow, dev scripts
- Pydantic v0.1 data contracts: task, events, execution plan, policy, validation
- Synthetic LangGraph cited market-research demo with mock tools
- Trace fixtures: success, expensive, failed_validation scenarios
- Adapter ports: LangGraph (stub), LiteLLM mock, OTel export interface
- Full documentation tree and three architecture decision records
- Baseline measurement report template and metric definitions
- Trace fixtures committed under `fixtures/traces/` (success, expensive, failed_validation)

### Verified (2026-07-14)

- `pytest` 23 passed; `ruff` clean; `mypy` clean (strict)
- Baselines are synthetic until real/anonymized partner traces are added

### Deferred

- SDK instrumentation and automatic event collection (Phase 1)
- Policy enforcement and budgets (Phase 2)
- Planner, routing, context manifests (Phase 3)
