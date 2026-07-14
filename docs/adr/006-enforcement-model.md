# ADR-006: Enforcement model (detection vs. action)

- **Status:** Accepted (Phase 2)
- **Date:** 2026-07-14

## Context

Phase 1 observes and flags waste but never acts. Phase 2 must turn detections into
safe, deterministic interventions (block / retry / pause / stop). The core design
question is how detection and action are separated and how the runtime applies an
action without silently changing behavior when enforcement is off.

## Decision

1. **Detection and action are separate.** `supervisor.policy.engine.evaluate(...)`
   detects matches and produces `PolicyDecision` records. `supervisor.policy.enforcement.Enforcer`
   decides whether a match should be *acted upon*, based on the policy `mode`
   (`observe` vs `enforce`) and the `Supervisor.enforce` flag.

2. **Opt-in enforcement.** `Supervisor(enforce=False)` (the default) is byte-for-byte
   identical to Phase 1 — every decision carries `action="observe"` and the runtime
   never raises or blocks. Enforcement is enabled per environment
   (`SUPERVISOR_ENFORCE=true` in the demo) or explicitly `Supervisor(enforce=True)`.

3. **Guard points at the call site.** The SDK `tool()` (and `retry()`) consult the
   enforcer before executing the external call. This works for any framework,
   including LangGraph graphs whose nodes call through `supervisor.tool()`. A
   callback-only short-circuit was rejected because LangChain callbacks cannot
   reliably prevent a tool from running (decision confirmed in the Phase 2 plan).

4. **Fail-safe.** If an enforcement decision cannot be applied, the runtime degrades
   to observe and logs; it never silently drops context or stops critical work
   without an audit record (`intervention.applied`).

## Action mapping

| Action | Runtime effect |
|---|---|
| `observe` | record only; no effect |
| `warn` | record; execution continues |
| `block` | prevent the call; deduplicate (return prior successful result) |
| `retry` | schedule a backoff retry |
| `pause` | raise `PauseForApproval` (human review) |
| `stop` | raise `StopRun`; finalize trace with `run.failed` + audit |

## Consequences

- Non-interference is guaranteed by construction (default `observe`).
- Enforcement is testable at the SDK level without a full graph.
- Adding a new action is a single branch in `Enforcer`/`Supervisor.act`.
