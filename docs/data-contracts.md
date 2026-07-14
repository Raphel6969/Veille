# Data Contracts

All contracts are versioned. Current schema version: **0.1.0**.

Python models live in `src/supervisor/contracts/`. This document mirrors their shape for non-Python consumers.

## Task Contract

```yaml
schema_version: "0.1.0"
task_id: cited-competitor-brief-001
task: Produce a cited competitor brief
required_outcome:
  - eight competitors
  - comparison table
  - current linked evidence for material claims
constraints:
  max_cost_usd: 1.00
  max_latency_seconds: 120
  allowed_models: []
  data_residency: null
quality_checks:
  - required_fields_present
  - citations_valid
  - no_duplicate_competitors
risk_level: medium  # low | medium | high
metadata: {}
```

## Run Event

```json
{
  "schema_version": "0.1.0",
  "event_id": "uuid",
  "run_id": "uuid",
  "event_type": "tool.completed",
  "timestamp": "2026-07-14T12:00:00Z",
  "step_id": "research",
  "agent_id": "researcher",
  "tool_name": "search_competitors",
  "duration_ms": 80.0,
  "cost_usd": 0.002,
  "status": "ok",
  "attributes": {
    "normalized_input_hash": "sha256..."
  }
}
```

### Event types

| Type | Description |
|---|---|
| `run.started` / `run.completed` / `run.failed` | Run lifecycle |
| `agent.started` / `agent.finished` | Agent step lifecycle |
| `model.requested` / `model.completed` | Model calls |
| `tool.requested` / `tool.completed` | Tool calls |
| `context.attached` | Context manifest attachment |
| `memory.retrieved` | Memory retrieval |
| `retry.scheduled` / `retry.completed` | Retry lifecycle |
| `policy.triggered` | Policy evaluation match |
| `intervention.applied` | Action taken |
| `validation.completed` | Outcome validation |

### Event attributes registry

The `attributes` object is open-ended. Phase 1 standardizes these keys (all optional unless noted):

| Attribute | Type | Emitted on | Meaning |
|---|---|---|---|
| `task_id` | string | `run.started` | Task contract id |
| `scenario` | string | `run.started` | Run tag (e.g. `success`, `expensive`) |
| `risk_level` | string | `run.started` | `low` \| `medium` \| `high` |
| `task_contract_met` | bool | `run.completed` / `run.failed` | Outcome validation result |
| `total_cost_usd` | number | `run.completed` / `run.failed` | Aggregated run cost |
| `duration_ms` | number | `run.completed` / `run.failed` | Total run wall time |
| `tool_name` | string | `tool.*` | Tool identifier |
| `normalized_input_hash` | string | `tool.*` | Stable hash of normalized tool input (dedup key) |
| `duplicate` | bool | `tool.*` | `true` when an equivalent prior *successful* call exists in the run |
| `failed` | bool | `tool.*` | `true` when the call errored |
| `error_message` | string | `tool.completed` | Error detail when `failed` |
| `model` | string | `model.*` | Model identifier |
| `prompt` | string | `model.requested` | Prompt text |
| `attempt` | int | `retry.*` | Current retry attempt (1-based) |
| `max_attempts` | int | `retry.*` | Retry budget for the step |
| `reason` | string | `retry.scheduled` / `policy.triggered` | Why the event fired |
| `policy_id` | string | `policy.triggered` | Matched policy identifier |
| `mode` | string | `policy.triggered` | `observe` \| `warn` \| `enforce` |
| `manifest` | object | `context.attached` | Context manifest snapshot |
| `check_id` | string | `validation.completed` | Quality check identifier |
| `passed` | bool | `validation.completed` | Check result |
| `message` | string | `validation.completed` | Check message |
| `action` | string | `intervention.applied` | `observe` \| `warn` \| `block` \| `pause` \| `retry` \| `stop` |
| `human_review_required` | bool | `intervention.applied` | `true` for `pause`/`handoff` |
| `reason` | string | `policy.triggered` / `intervention.applied` | Why the policy matched/acted |

## Run Event Batch

Used for replay and fixtures:

```json
{
  "schema_version": "0.1.0",
  "run_id": "uuid",
  "task_id": "cited-competitor-brief-001",
  "events": [],
  "metadata": {
    "scenario": "success",
    "task_contract_met": true,
    "total_cost_usd": 0.05
  }
}
```

## Execution Plan (skeleton)

```json
{
  "schema_version": "0.1.0",
  "plan_id": "plan-001",
  "task_id": "cited-competitor-brief-001",
  "selected_tier": "balanced",
  "tier_options": [],
  "steps": [
    {
      "step_id": "research",
      "role": "researcher",
      "description": "Collect competitor candidates",
      "depends_on": [],
      "expected_inputs": ["query"],
      "expected_outputs": ["competitors"],
      "capability_requirements": ["tool_use"]
    }
  ],
  "policy_limits": {}
}
```

## Policy Definition (skeleton)

```yaml
schema_version: "0.1.0"
policy_id: duplicate_search_protection
name: duplicate_search_protection
condition: same_tool_and_normalized_input_seen_twice
mode: observe  # observe | warn | enforce
action: warn   # warn | block | pause | retry | reroute | handoff | stop
reason_template: "Equivalent search request already occurred in this run."
enabled: true
```

## Validation Report

```json
{
  "schema_version": "0.1.0",
  "run_id": "uuid",
  "task_id": "cited-competitor-brief-001",
  "task_contract_met": true,
  "checks": [
    {
      "check_id": "citations_valid",
      "passed": true,
      "message": "Every material claim must have a linked source."
    }
  ],
  "confidence": 1.0,
  "unresolved_issues": [],
  "human_review_required": false
}
```

## Versioning rules

- Bump `schema_version` on breaking changes.
- Contract tests must pass round-trip serialization for every model.
- New fields should be optional with defaults when extending.
