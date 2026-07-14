# Policy Engine

> **Status:** Phase 2 implements **enforcement** (block / retry / pause / stop) opt-in via `Supervisor(enforce=True)` or `SUPERVISOR_ENFORCE=true`. Default remains observe-only.

## Phase 1 observe mode

`src/supervisor/policy/engine.py` provides `evaluate_observe(batch)` which scans a `RunEventBatch` and returns `PolicyObservation` records. It never mutates execution or emits interventions.

Built-in policies (`DEFAULT_OBSERVE_POLICIES`):

| Policy id | Detects | Key |
|---|---|---|
| `duplicate_tool_call` | Same `tool_name` + `normalized_input_hash` seen after a prior **successful** call | `duplicate=True` on `tool.*` |
| `retry_storm` | `retry.attempt` exceeds `RETRY_BUDGET` (default 5) | `policy.triggered` |
| `cost_overrun` | `total_cost_usd` > `max_cost_usd` (from task contract) | `policy.triggered` |
| `validation_failure` | `validation.completed` with `passed=False` | `policy.triggered` |

Each observation carries `policy_id`, `mode="observe"`, `reason`, and an advisory `intervention` (e.g. `dedupe`, `backoff`, `review`). The CLI surfaces these via `explore --policy`.

## Policy modes

| Mode | Behavior |
|---|---|
| `observe` | Record policy match; do not change execution |
| `warn` | Emit warning; execution continues unless configured otherwise |
| `enforce` | Apply the configured action |

All policies **default to observe** until explicitly approved for warn or enforce.

## Policy actions

| Action | Description |
|---|---|
| `warn` | Log and surface reason to operator |
| `block` | Prevent the triggering action |
| `pause` | Pause run for approval |
| `retry` | Schedule backoff retry |
| `reroute` | Select alternate model/provider |
| `handoff` | Escalate to human review |
| `stop` | Stop run while preserving trace |

## Phase 2 deterministic policies (implemented)

Policies live in `src/supervisor/policy/engine.py` (`DEFAULT_ENFORCE_POLICIES`). Each
defaults to `enforce` mode with a configured action; they only act when the runtime
is in enforcement mode.

| Policy id | Detects | Enforce action |
|---|---|---|
| `duplicate_tool_protection` | Same `tool_name` + `normalized_input_hash` after a prior **successful** call | `block` (dedupe) |
| `retry_budget` | `retry.scheduled` count exceeds `RETRY_BUDGET` (default 5) | `stop` |
| `cost_budget` | `total_cost_usd` > `max_cost_usd` (task contract) | `stop` |
| `stall_protection` | `tool.completed` `duration_ms` > `max_latency_seconds` | `stop` |
| `loop_protection` | identical `(tool_name, hash)` call repeats > `LOOP_LIMIT` (3) | `stop` |

`evaluate(batch, enforce=..., max_cost_usd=..., max_latency_seconds=...)` returns
`PolicyDecision` records. With `enforce=False` every decision is `action="observe"`
and the runtime is unchanged. With `enforce=True`, `ENFORCE`-mode matches carry their
configured action and `applied=True`.

The runtime applies decisions through `Supervisor.act(decision)`:
`block` → dedupe (return prior result), `stop` → raise `StopRun`, `pause` → raise
`PauseForApproval`, `warn`/`observe` → record only. See [ADR-006](adr/006-enforcement-model.md).

Budgets are tracked per run by `BudgetTracker` (`src/supervisor/policy/budgets.py`)
behind a `CounterBackend` port (in-memory default; Redis optional). See
[ADR-007](adr/007-budget-backend-port.md).

## Phase 2 deterministic policies (planned)

1. Cost tier planner integration (Phase 3)
2. Semantic / learned detection (Phase 4+)

## Safety rules

- Every intervention must include a structured, human-readable reason.
- Fail safely; never silently remove context or stop critical work without audit.
- Enforcement requires explicit approval per environment.
- Feature-flag each policy independently.

## Example (Phase 2)

```yaml
policy_id: duplicate_search_protection
condition: same_tool_and_normalized_input_seen_twice
mode: observe
action: block
reason_template: "Equivalent search request already occurred in this run."
```

See [data contracts](data-contracts.md) for the full schema.
