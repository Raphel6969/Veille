# Phase 2 — Deterministic protection: Implementation Plan

**Status:** Proposed — awaiting approval. Do not begin until the Phase 2 approval gate is approved.

**Carried over from Phase 1:** Phase 1 is implemented and committed on `pre_dev` (`f847db0`): SDK, LangGraph callback instrumentation, `RunSummary` analytics, observe-only policy engine, OTel export, and the run-explorer CLI. All policies currently run in **observe** mode and never alter execution. Phase 2 turns detection into safe, deterministic **action**.

## Goal

Make the Supervisor **act** on detected waste and risk with deterministic, auditable interventions — block, retry-with-backoff, pause, or stop — while remaining safe by default (observe mode stays the default; enforcement is explicitly opted in per environment).

## Non-goals (explicitly excluded)

- No model routing, no context mutation/compression, no cost-tier planning (Phase 3).
- No semantic / learned detection (Phase 4+). Exact, deterministic rules only.
- No Next.js control-plane UI. Enforcement is observable via the CLI, OTel, and audit records.
- No durable audit store wiring beyond an in-memory + append-only local log; Postgres/Redis are optional backends behind ports.

## User-visible outcome

Running the demo (or any wrapped LangGraph agent) with enforcement enabled yields:

1. **Enforced budgets** — a run that exceeds `max_cost_usd` / retry budget / latency deadline is stopped or paused with a human-readable reason.
2. **Duplicate elimination** — an equivalent *successful* tool call already seen in the run is blocked (or deduplicated) instead of re-executed.
3. **Retry governance** — retries beyond `RETRY_BUDGET` are blocked; the supervisor can schedule a backoff retry on transient failures.
4. **Loop / cycle protection** — repeated identical step sequences are detected and stopped.
5. **Full audit trail** — every intervention emits `intervention.applied` with `policy_id`, `action`, `reason`, and a `human_review_required` flag where applicable.
6. **Safe default** — with enforcement off (default), behavior is byte-identical to Phase 1.

## Architecture and design decisions

### D1. Detection stays separate from action

`src/supervisor/policy/engine.py` keeps `evaluate_observe(batch)` (unchanged). Phase 2 adds `evaluate(batch, mode)` that, for `warn`/`enforce` policies, returns `PolicyDecision` records carrying a recommended `action`. A new `src/supervisor/policy/enforcement.py` applies decisions through an `Enforcer` that the runtime consults **before** executing a guarded step.

Hard rule: enforcement only runs when `SUPERVISOR_ENFORCE=true` (or `Supervisor(enforce=True)`). Otherwise the engine returns observe-mode decisions and the runtime ignores `action`.

### D2. Enforcement points in the runtime

The `Supervisor` exposes guard hooks the agent/adapter calls:

- `supervisor.guard_tool(step_id, agent_id, tool_name, input)` → returns either `Allow` or `Block(reason, policy_id)` (and records the decision). The agent wraps each tool call through this; the LangGraph adapter also consults it in `on_tool_start`.
- `supervisor.guard_retry(step_id, attempt)` → `Allow` / `Block` once `RETRY_BUDGET` is exhausted.
- `supervisor.guard_step(step_id, deadline)` → `Allow` / `Block` on stall/timeout.
- `supervisor.guard_loop(state_hash)` → `Allow` / `Block` on repeated identical state.

When a guard returns `Block`, the runtime raises `InterventionError(action, reason, policy_id)`. The LangGraph adapter maps:
- `block` → skip the tool (return a guarded `blocked` result, no external call)
- `retry` → raise a `RetryWithBackoff` signal the node catches
- `pause` → raise a graph interrupt (`PauseForApproval`) for human review
- `stop` → raise `StopRun` and finalize the trace with `run.failed` + audit

> Decision to confirm: tool guards are consulted at the call site via an explicit `guard_tool` wrapper (recommended — works for any framework) rather than relying solely on LangGraph callbacks (which cannot cleanly short-circuit a tool). The adapter provides a convenience wrapper so existing agents opt in with one line.

### D3. Deterministic policy set (Phase 2)

| Policy id | Condition | Default mode | Enforce action |
|---|---|---|---|
| `cost_budget` | `total_cost_usd` > `max_cost_usd` | observe → enforce | `stop` (or `warn`) |
| `retry_budget` | `retry.attempt` > `RETRY_BUDGET` (5) | observe → enforce | `block` |
| `duplicate_tool_call` | same `tool_name` + `normalized_input_hash` after a prior **successful** call | observe → enforce | `block` (dedupe) |
| `stall_protection` | step exceeds `max_latency_seconds` (from task contract) | observe → enforce | `pause` / `stop` |
| `loop_protection` | identical step state repeats `N` times | observe → enforce | `stop` |

All remain `observe` until explicitly enabled; enabling is per-environment and recorded in the run metadata (`enforcement_enabled: true`).

### D4. Budgets and counters — `src/supervisor/policy/budgets.py`

In-memory `BudgetTracker` per run: cost, retry counts per step, latency windows. A `CounterBackend` port allows an optional Redis backend (roadmap: Redis Phase 2+) with in-memory as the default so tests and the demo need no infrastructure. `RETRY_BUDGET` moves from a constant to a configurable limit sourced from the task contract / policy definition.

### D5. Audit and human review

Every applied (or recommended) action emits `intervention.applied` with `policy_id`, `mode`, `action`, `reason`, and `human_review_required` (`true` for `pause`/`handoff`). An append-only local audit log (`fixtures/audit/` or configured path) records each decision for post-hoc review. `ValidationReport.human_review_required` is set when any `pause`/`handoff` fired.

### D6. Safety rules (carried + extended)

- Fail safe: if the enforcer itself errors, fall back to `observe` and log; never silently drop context or stop critical work without audit.
- Every intervention must include a structured, human-readable reason.
- Enforcement requires explicit opt-in; default is observe.
- Feature-flag each policy independently (mode lives in the `PolicyDefinition`).

## Files / components expected to change

| Path | Change |
|---|---|
| `src/supervisor/policy/engine.py` | Add `evaluate(batch, mode)` + `PolicyDecision` |
| `src/supervisor/policy/enforcement.py` (new) | `Enforcer`, guard hooks, `InterventionError`/`RetryWithBackoff`/`PauseForApproval`/`StopRun` |
| `src/supervisor/policy/budgets.py` (new) | `BudgetTracker`, `CounterBackend` port + in-memory impl |
| `src/supervisor/sdk/supervisor.py` | `enforce` flag; `guard_tool` / `guard_retry` / `guard_step` / `guard_loop`; emit `intervention.applied` |
| `src/supervisor/adapters/langgraph/adapter.py` | Consult guards in `on_tool_start`; map actions to interrupts/exceptions |
| `src/supervisor/contracts/events.py` | `intervention.applied` attributes (`action`, `policy_id`, `reason`, `human_review_required`) |
| `examples/cited_market_research/agent.py` | Opt-in enforcement via `SUPERVISOR_ENFORCE`; route tools through `guard_tool` |
| `tests/policy/` | Enforcement unit tests (block/retry/stop/pause, safe-default, audit) |
| `tests/adapters/` | Adapter maps guards to interrupts |
| `tests/examples/` | `expensive` scenario under enforcement shows blocked duplicate + stopped run |

## Documentation deliverables

- **ADR-006:** Enforcement model — detection vs. action, guard points, fail-safe default.
- **ADR-007:** Budget/counter backend port (in-memory default, Redis optional).
- `docs/data-contracts.md`: extend the event attributes registry with `intervention.applied` keys (`action`, `policy_id`, `reason`, `human_review_required`).
- `docs/policy-engine.md`: document `warn`/`enforce` modes, actions, and the deterministic policy set with default modes.
- `docs/architecture.md` / `docs/runtime-chain.md`: mark *Detect Problems* and *Intervene* as implemented (enforce optional).
- `docs/operations.md`: document enabling enforcement (`SUPERVISOR_ENFORCE`), audit log location, runbooks for switching a policy to enforce.
- `README.md`, `docs/roadmap.md`, `CHANGELOG.md`: update Phase 2 status after completion.

## Tests and acceptance criteria

- **Safe default:** with enforcement off, Phase 2 output is byte-identical to Phase 1 (non-interference regression).
- **Enforcement changes behavior:** on the `expensive` fixture with enforcement, the duplicate `search_competitors` is blocked and the retry storm is stopped at `RETRY_BUDGET`.
- **Action mapping:** `block` skips the external call; `stop` finalizes the trace with `run.failed` + audit; `pause` raises a review interrupt; `retry` triggers backoff.
- **Budgets:** `BudgetTracker` enforces cost/retry/latency limits; Redis path optional and tested separately (or skipped when unavailable).
- **Audit:** every intervention emits `intervention.applied` and is appended to the audit log; `human_review_required` set for `pause`/`handoff`.
- **Fail-safe:** an enforcer exception degrades to observe and is logged; no silent context loss.
- **Contract:** `intervention.applied` schema round-trips; new attributes documented and tested.

**Master-prompt acceptance (Phase 2):**

- Waste is not only flagged but prevented (duplicate calls, runaway retries, budget overruns). ✓
- Every action is auditable and explainable. ✓
- Safe default: no behavior change unless explicitly enabled. ✓
- Trace/event schema contract tests pass. ✓

## Risks, assumptions, dependencies

- **Short-circuit difficulty in LangGraph callbacks** — mitigated by explicit `guard_tool` call-site wrapper (decision D2 to confirm).
- **Retry semantics** — supervisor-driven backoff must compose with agent-internal retry; define a single owner of retries (supervisor) to avoid double-counting.
- **Redis optional** — cross-process budgets only matter at scale; single-process in-memory is sufficient for Phase 2 demos and tests.
- **Blast radius of `stop`** — must preserve the full trace and emit `run.failed` so post-mortem is possible.
- **Enforcement opt-in** — default observe to protect existing integrations; gated by `SUPERVISOR_ENFORCE`.

---

## Phase 2 approval gate

```
Phase 2 is ready to begin.

Goal: Turn Phase 1 observation into safe, deterministic action.

Scope:
  - Enforcement engine: detection separated from action
  - Guard points (tool / retry / step / loop) consulted before execution
  - Deterministic policies: cost budget, retry budget, duplicate-tool,
    stall protection, loop protection
  - Actions: warn, block, retry-with-backoff, pause, stop (handoff stub)
  - Budget/counter tracker (in-memory default, Redis optional)
  - Full audit trail (intervention.applied + append-only log)
  - Safe default: observe unless explicitly enabled

Not in scope:
  - model routing, context mutation/compression, cost-tier planning (Phase 3)
  - semantic / learned detection (Phase 4+)
  - Next.js control-plane UI

Key decisions / assumptions:
  - call-site guard_tool wrapper (not callback-only short-circuit)
  - enforcement opt-in via SUPERVISOR_ENFORCE (default observe)
  - fail-safe: enforcer errors degrade to observe
  - Redis optional backend behind a port

Validation:
  - pytest: enforcement behavior, safe-default regression, audit,
    budget limits, adapter action mapping
  - ruff + mypy clean
  - demo runs without API keys on Python 3.14

Risks / questions:
  - LangGraph short-circuit approach (guard wrapper vs callback)
  - single owner of retries (supervisor) to avoid double-count
  - blast radius of stop (preserve trace + run.failed)

May I implement Phase 2 now?
```
