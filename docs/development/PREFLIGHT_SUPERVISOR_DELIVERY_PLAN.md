# Preflight Supervisor Delivery Plan

## Objective

Deliver VEILLE as a production-pilot-ready **Preflight Supervisor**: before an
agent executes, VEILLE receives a user request and master context, produces an
explainable task contract, execution plan, per-role context manifests,
cost/latency options, and model-routing recommendations, then executes through
the same Runtime Supervisor after explicit approval.

The product rule is non-negotiable:

> VEILLE has one Runtime Supervisor and many entry points. SDK, CLI, IDE, and
> daemon integrations are thin adapters over the same contracts, decisions,
> policies, execution path, and audit trail.

## Delivery rules

- Each commit must be independently testable and leave the runtime compatible.
- Observe/advisory mode is the default. Context mutation, routing, caching, and
  enforcement require explicit configuration and a human-readable reason.
- No entry point may implement planning, policy, routing, or context behavior.
- Every optimization is measured against validation/task success, not cost alone.
- Complete a phase's verification and obtain approval before starting the next.

## Current baseline

Existing capabilities include task and event contracts, a `Supervisor` SDK,
LangGraph instrumentation, policies/enforcement, planner/context/router
components, optimization, memory governance, a local console, and real-world
demo workflows. Planning, context, and routing are currently advisory SDK
capabilities; they are not yet one cohesive preflight product path.

The current Adoption Foundation branch adds the first thin entry points:
`import veille` and `veille exec <app.py>`.

---

## Phase 0 — Lock the runtime boundary and baseline

**Goal:** commit the current foundation and define the integration contract all
future entry points use.

**Status:** Complete (2026-07-15).

**Exit:** one documented runtime boundary, no duplicate feature logic, and a
reproducible baseline suite.

| Commit | Change | Verification |
|---|---|---|
| `feat(runtime): establish public veille SDK and execution envelope` | Commit `import veille`, `supervisor.runtime`, and `veille exec`. | Runtime/CLI tests; package import test. |
| `docs: record one-runtime adoption rule` | Commit Golden Rule architecture, adoption guide, roadmap, and changelog updates. | Links and terminology reviewed. |
| `test: capture current end-to-end baselines` | Add stable golden traces for the current market-research and real-world workflows. | Full suite; summaries stored for comparison. |
| `chore: make repository formatting baseline clean` | Format the existing `design_partner_demo.py` drift; do not mix behavior changes. | `ruff format --check .`. |

**Non-goals:** new planning behavior, daemon, IDE extension, automatic provider
instrumentation.

## Phase 1 — Preflight contracts and decision record

**Goal:** make “request before execution” a first-class runtime input/output.

**Status:** In progress.

**Exit:** VEILLE can serialize, validate, explain, and replay a complete
preflight proposal without executing an agent.

| Commit | Change | Verification |
|---|---|---|
| `feat(contracts): add preflight request and proposal schemas` | Add versioned `PreflightRequest`, `RoleSpec`, `ContextSource`, `CostOption`, `RouteRecommendation`, `PreflightProposal`, and `ApprovalDecision`. | Schema round trips, backwards-compatibility tests, JSON fixtures. |
| `feat(runtime): add preflight decision ledger` | Add structured decision IDs/reasons that connect task, plan, manifests, routes, estimates, and validation criteria. | Every proposal field has a reason/provenance test. |
| `feat(planning): build proposal from task and master context` | Compose the existing planner, context engine, and router behind `RuntimeSupervisor.preflight()`. | Deterministic golden proposal for a research task. |
| `feat(cost): expose comparable cost and latency options` | Produce Minimum, Balanced, High Quality, Maximum Assurance ranges with explicit trade-offs. | Tier ordering, budget/risk constraints, clear recommendation tests. |
| `docs: specify preflight API and decision semantics` | Update contracts, runtime chain, architecture, and ADR. | Documentation examples execute in tests. |

**Non-goals:** automatically changing an application’s calls; LLM-powered task
decomposition; production storage.

## Phase 2 — Safe plan application in the runtime

**Goal:** execute an approved proposal through the existing Supervisor.

**Exit:** approved plans supply the correct role-specific context and routing to
an instrumented workflow, while observe mode remains behavior-preserving.

| Commit | Change | Verification |
|---|---|---|
| `feat(runtime): add approved-plan execution session` | Introduce a `RunSession` that binds one approved proposal to one `Supervisor` run. | Session lifecycle emits proposal and run correlation IDs. |
| `feat(context): provide role-context resolver` | Resolve a manifest into safe included/excluded/compressed context slices, with confidentiality boundaries. | Role isolation and redaction tests. |
| `feat(routing): apply approved route recommendations` | Allow an adapter to request a step’s approved model route; preserve fallback and policy checks. | Routing is advisory unless activation is explicitly enabled. |
| `feat(validation): bind completion to the task contract` | Make required fields, citations, and custom deterministic checks part of final run status. | A cheap plan cannot pass when validation regresses. |
| `test(runtime): prove observe-mode non-interference` | Replay the same instrumented workflow with preflight disabled/observe/active. | Same business output in observe mode; active changes are auditable. |

**Non-goals:** autonomous model selection outside approved allowlists; silent
context deletion; learned policies.

## Phase 3 — First real framework path: LangGraph

**Goal:** make the preflight proposal drive a real multi-role LangGraph workflow.

**Exit:** one user request demonstrably becomes role-specific work before model
and tool calls occur.

| Commit | Change | Verification |
|---|---|---|
| `feat(langgraph): map graph nodes to preflight roles and steps` | Extend the existing adapter with approved-plan/session hooks. | Callback events correlate node, role, manifest, and route. |
| `feat(example): add a real preflight research workflow` | Replace demo-only narration with an end-to-end read-only workflow using real-shaped input/context. | Offline fixture and safe local HTTP integration test. |
| `feat(example): add deliberately wasteful control scenario` | Include irrelevant context, duplicate lookup, and weak route baselines. | Before/after comparison validates outcome equivalence or improvement. |
| `test(adapter): add golden-plan replay coverage` | Replay sanitized requests and assert plan, context allocations, routes, and validation. | Golden traces stable across releases. |
| `docs: publish framework integration recipe` | Explain the smallest LangGraph integration and all activation flags. | Recipe is smoke-tested. |

**Non-goals:** deep support for CrewAI/OpenAI Agents SDK; general automatic graph
generation.

## Phase 4 — SDK and CLI product experience

**Goal:** make the preflight flow easy to try on a developer’s own project.

**Exit:** a developer can inspect, approve, run, and compare a plan locally.

| Commit | Change | Verification |
|---|---|---|
| `feat(sdk): expose preflight and approved-run API` | Add stable `veille.preflight(...)` and `proposal.approve()`/session APIs; retain old imports. | Copy-paste SDK quickstart test. |
| `feat(cli): add veille preflight` | Accept request text, task-contract file, and context sources; print/save a proposal. | JSON and human-readable output fixtures. |
| `feat(cli): add veille run --proposal` | Require explicit approval for active routing/context application and persist the linked trace. | Refusal without approval; successful approved run test. |
| `feat(cli): add baseline comparison report` | Compare baseline vs supervised cost, latency, calls, validation, and quality checks. | Known duplicate/wasteful scenario test. |
| `docs: publish dogfood and demo runbooks` | Add personal-use, local safety, and live-demo instructions. | Commands smoke-tested from a clean environment. |

**Important boundary:** `veille exec app.py` remains an observe-mode envelope
unless the application uses an SDK/framework adapter. Do not claim arbitrary
application preflight orchestration without integration points.

## Phase 5 — Console as a decision-and-evidence view

**Goal:** make the preflight decision understandable without creating a second
runtime.

**Exit:** the console renders the same persisted proposal and run events emitted
by the runtime.

| Commit | Change | Verification |
|---|---|---|
| `feat(console): add proposal read models and API endpoints` | Read-only API over runtime proposal/run records. | Contract tests prove API is a projection, not recomputation. |
| `feat(ui): add preflight review page` | Show task contract, plan graph, per-role context, routes, cost options, and approval state. | Component and API tests. |
| `feat(ui): add baseline-versus-run comparison` | Visualize validated quality, spend, latency, and interventions. | Golden fixture screenshots/Playwright flow. |
| `feat(console): add redaction-first trace views` | Ensure raw prompts/payloads stay hidden unless explicitly retained. | Redaction regression tests. |

## Phase 6 — Durable pilot runtime and daemon host

**Goal:** support real multi-process pilots without making a hosted platform
prematurely.

**Exit:** a locally/self-hosted daemon hosts the same runtime state and audit
path, with reliable recovery and operational visibility.

| Commit | Change | Verification |
|---|---|---|
| `feat(storage): add durable run/proposal/audit repository port` | Define repository interfaces; ship SQLite/local default and Postgres implementation behind configuration. | Restart/replay and migration tests. |
| `feat(daemon): host runtime API and worker` | Add `veille daemon` for receiving proposals/runs and exporting OTel; it invokes the shared runtime only. | SDK/CLI/daemon produce compatible event batches. |
| `feat(daemon): add authenticated project and environment boundaries` | Project IDs, API tokens, configuration scoping, and safe secret resolution. | Cross-project isolation and secret-redaction tests. |
| `feat(ops): add health, readiness, retry, and backpressure controls` | Health endpoints, bounded queues, recovery, structured logs, safe shutdown. | Fault-injection and restart tests. |
| `docs: add self-hosted pilot runbook` | Docker/local deployment, backup/retention, incident and rollback steps. | Clean-host smoke test. |

**Non-goals:** multi-region SaaS, billing, SSO, autonomous enforcement.

## Phase 7 — IDE integration as a thin client

**Goal:** give local developers useful feedback without duplicating runtime
logic.

**Exit:** one IDE extension launches/reads the same CLI or daemon runs.

| Commit | Change | Verification |
|---|---|---|
| `docs: choose first IDE and extension protocol` | Default to VS Code only if pilot users validate it. | ADR records scope and API boundary. |
| `feat(vscode): run/inspect preflight via CLI or daemon` | Provide command palette actions, proposal preview, and trace links. | Extension integration tests against local daemon/CLI. |
| `feat(vscode): add configuration and safety UX` | Make activation modes, project selection, and data boundaries visible. | No active action without explicit confirmation test. |

## Phase 8 — Production-pilot proof and launch package

**Goal:** prove usefulness on real, permissioned workflows before broad claims.

**Exit:** 3–5 design partners can independently run VEILLE on safe workloads
and evaluate measurable, validated outcomes.

| Commit | Change | Verification |
|---|---|---|
| `test(pilot): add sanitized golden-trace suite` | Capture representative partner-approved traces with retention/redaction controls. | Deterministic replay in CI. |
| `feat(evaluation): add quality-and-savings scorecard` | Compare task success, validation, cost, latency, false interventions, and user acceptance. | Scorecard cannot report savings as success when validation drops. |
| `docs: publish pilot integration and security checklist` | Define prerequisites, supported boundaries, rollback, and known limits. | Design-partner review. |
| `docs: publish evidence-backed demo and launch material` | Use one real, permissioned before/after workflow; make claims only from measured evidence. | Demo rehearsal and release checklist. |

## Release gates

| Gate | Required before claiming it |
|---|---|
| Developer preview | Phases 0–4 complete; local SDK/CLI workflow with reproducible proposal and validation. |
| Pilot-ready | Phase 6 complete; durable storage, isolation, recovery, runbooks, and real-workflow evidence. |
| IDE preview | Phase 7 complete; IDE acts only as a thin client over runtime decisions. |
| Broad production claim | Phase 8 evidence plus security review, operational SLOs, and explicit supported-workload limits. |

## Suggested next implementation phase

Begin **Phase 1 — Preflight contracts and decision record**. It creates the
single product object every future entry point needs and turns existing advisory
planner/context/router components into one coherent runtime operation.
