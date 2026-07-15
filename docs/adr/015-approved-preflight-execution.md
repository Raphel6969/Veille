# ADR-015: Approved preflight execution

## Status

Accepted — Adoption Foundation Phase 2.

## Decision

Only an `ApprovalDecision(status="approved")` matching a proposal may create an
`ApprovedRunSession`. The session is a thin wrapper over the existing
`Supervisor`; it applies approved role context and routing while emitting audit
facts. Advisory preflight does not alter normal model execution.

## Consequences

- Context and routing activation is explicit and traceable.
- Rejected/mismatched proposals cannot execute.
- The runtime remains the single policy and event implementation point.
