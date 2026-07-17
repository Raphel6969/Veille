# ADR-014: Preflight proposal boundary

## Status

Accepted — Adoption Foundation Phase 1.

## Context

VEILLE has separate planner, context-engine, and model-router components.
Calling them independently prevents SDK, CLI, daemon, and IDE entry points from
presenting one coherent pre-execution decision.

## Decision

Introduce versioned `PreflightRequest` and `PreflightProposal` contracts and
compose existing components through `Supervisor.preflight()`. A proposal
contains an execution plan, cost options, per-role context manifests, route
recommendations, and a decision ledger.

Proposal and plan IDs are deterministic for identical request content. This is
advisory-only: it starts no run, emits no events, and does not modify context or
routing. `ApprovalDecision` records the future approval boundary.

## Consequences

- Every entry point gets one stable object to render, store, approve, and later
  execute through the Runtime Supervisor.
- Preflight composes existing planning/context/routing logic; it is not a
  parallel decision engine.
- Applying a proposal is deferred to Phase 2.
