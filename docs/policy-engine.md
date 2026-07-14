# Policy Engine

> **Status:** Planned for Phase 2. Phase 0 defines the policy contract schema only.

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

## Phase 2 deterministic policies (planned)

1. Cost budget
2. Timeout / stall protection
3. Retry budget
4. Duplicate tool call (tool name + normalized input hash)
5. Exact cycle / loop detection

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
