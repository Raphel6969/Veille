# Data Contracts

All contracts are versioned. Current schema version: **0.2.0**.

Python models live in `src/supervisor/contracts/`. This document mirrors their shape for non-Python consumers.

> **0.2.0 (Phase 4)** is additive over 0.1.0: new `optimization.*` event types and
> optional attributes on `tool.requested` / `model.requested`. 0.1.0 events remain valid.

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
| `memory.retrieved` | Memory retrieval + governance manifest |
| `memory.expired` | Memory expiry candidate / explicit removal (audited) |
| `retry.scheduled` / `retry.completed` | Retry lifecycle |
| `policy.triggered` | Policy evaluation match |
| `intervention.applied` | Action taken |
| `optimization.recommended` | Cache hit that *would* have served (dry-run) |
| `optimization.applied` | Cache hit that *was* served (active) |
| `validation.completed` | Outcome validation |

### Event attributes registry

The `attributes` object is open-ended. Phase 1 standardizes these keys (all optional unless noted):

| Attribute | Type | Emitted on | Meaning |
|---|---|---|---|
| `task_id` | string | `run.started` | Task contract id |
| `scenario` | string | `run.started` | Run tag (e.g. `success`, `expensive`) |
| `risk_level` | string | `run.started` | `low` \| `medium` \| `high` |
| `tier` | string | `run.started` | Planned `PlanTier` (`minimum` \| `balanced` \| `high_quality` \| `maximum_assurance`) when planning is enabled |
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
| `routing_tier` | string | `model.requested` | `PlanTier` selected by `route_model` (advisory, Phase 3) |
| `routing_capability` | string | `model.requested` | Capability used for routing (e.g. `research`) |
| `routing_reason` | string | `model.requested` | Why the router chose the model |
| `included` | list[string] | `context.attached` | Context slices included for the step |
| `excluded` | list[string] | `context.attached` | Context slices excluded for the step |
| `compressed` | list[string] | `context.attached` | Long slices compressed for the step |
| `estimated_tokens` | int | `context.attached` | Estimated token cost of the attached context |
| `reason` | string | `context.attached` | Why this context manifest was built |
| `attempt` | int | `retry.*` | Current retry attempt (1-based) |
| `max_attempts` | int | `retry.*` | Retry budget for the step |
| `reason` | string | `retry.scheduled` / `policy.triggered` | Why the event fired |
| `policy_id` | string | `policy.triggered` | Matched policy identifier |
| `mode` | string | `policy.triggered` | `observe` \| `warn` \| `enforce` |
| `manifest` | object | `context.attached` | Context manifest snapshot |
| `match_type` | string | `tool.requested` / `model.requested` | `exact` \| `semantic` when a near-duplicate is detected |
| `similarity` | float | `tool.requested` / `model.requested` | Jaccard/diff similarity (0–1) |
| `cache_key` | string | `optimization.*` | Semantic cache key of the served/near-duplicate call |
| `cache_hit` | bool | `optimization.*` / `tool.completed`(served) | `true` when a cache entry matched |
| `estimated_savings_usd` | number | `optimization.*` | Cost avoided by serving from cache |
| `included` | list[string] | `memory.retrieved` | Memory ids included for the step |
| `excluded` | list[string] | `memory.retrieved` | Memory ids excluded (low score / stale / drift) |
| `stale` | list[string] | `memory.retrieved` | Memory ids flagged stale (recency/confidence) |
| `drift` | list[string] | `memory.retrieved` | Memory ids flagged drift (content changed vs baseline) |
| `scores` | object | `memory.retrieved` | Memory id → governance score |
| `memory_id` | string | `memory.expired` | Memory id due for / subject to removal |
| `reason` | string | `memory.expired` | `ttl_elapsed` \| `explicit_removal` |
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
  "tier_options": [
    {
      "tier": "balanced",
      "cost_multiplier": 1.0,
      "latency_multiplier": 1.0,
      "recommended": true
    }
  ],
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

### PlanTier vocabulary (Phase 3)

| Tier | Meaning |
|---|---|
| `minimum` | Lowest assurance, cheapest, fastest |
| `balanced` | Default trade-off for medium-risk tasks |
| `high_quality` | Extra review/coverage for high-risk tasks |
| `maximum_assurance` | Strongest checks (e.g. human-in-the-loop) for critical tasks |

`TierEstimate` carries relative `cost_multiplier` / `latency_multiplier` (not
absolute currency). Exactly one tier option is flagged `recommended`, matching
`selected_tier`.

## Preflight Request and Proposal (Adoption Foundation Phase 1)

Preflight is an advisory, request-before-execution boundary. A caller supplies a
task contract and labelled master-context slices. The Runtime Supervisor returns
a deterministic `PreflightProposal`; it does not start a run, mutate application
context, or route a live model call.

```json
{
  "schema_version": "0.1.0",
  "proposal_id": "stable-uuid",
  "status": "advisory",
  "execution_plan": { "selected_tier": "balanced" },
  "cost_options": [{ "tier": "minimum" }, { "tier": "balanced", "recommended": true }],
  "context_manifests": [{ "step_id": "research", "role": "researcher" }],
  "route_recommendations": [{ "step_id": "research", "model": "mock-research" }],
  "decision_ledger": [{ "category": "execution_plan", "reason": "Selected balanced tier..." }]
}
```

Every plan, context, and route decision has a human-readable reason and
provenance. `ApprovalDecision` records the future approval boundary; Phase 1
does not apply it.

## Memory Record & Manifest (Phase 5, opt-in)

```json
{
  "schema_version": "0.2.0",
  "id": "mem-001",
  "tenant": "default",
  "content": "Prior query context: AI runtime supervision competitors 2026",
  "tier": "long",
  "provenance": { "run_id": "run-1", "step_id": "research", "agent_id": "researcher" },
  "confidence": 0.9,
  "created_at": "2026-07-14T12:00:00Z",
  "last_accessed": "2026-07-14T12:00:00Z",
  "access_count": 1,
  "ttl_seconds": null,
  "baseline_hash": "sha256..."
}
```

A `memory.retrieved` event carries a governance manifest:

```json
{
  "role": "researcher",
  "query": "AI runtime supervision competitors",
  "included": ["mem-001"],
  "excluded": [],
  "stale": [],
  "drift": [],
  "scores": { "mem-001": 0.82 },
  "reason": "Role 'researcher' retrieved 1 of 1 candidate memories (stale=0, drift=0)."
}
```

Tiers: `working` | `short` | `long` | `archive`. Scoring is metadata-driven
(recency/usage/provenance/confidence); no embeddings by default.

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
