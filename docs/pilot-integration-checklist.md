# Pilot Integration and Security Checklist

Use this checklist for each permissioned VEILLE Phase 8 pilot. It defines the supported boundary; it is not a production certification.

## Before connecting a workflow

- Name one project owner and obtain written permission for the selected workload.
- Use a read-only workflow with mock or non-sensitive data for the first run.
- Keep VEILLE in advisory mode until the owner explicitly approves a proposal.
- Bind the daemon to loopback or an authenticated TLS reverse proxy; use a unique project token.
- Do not submit prompts, credentials, personal data, proprietary source material, or production secrets as pilot evidence.
- Agree the retention window, deletion contact, rollback owner, and incident contact before capture.

## Capture and evaluation

- Store only `sanitize_batch()` output in the pilot evidence set.
- Create one baseline and one supervised run for the same task contract and validation criteria.
- Run `scorecard(baseline, supervised)` and retain the complete result beside the trace pair.
- Claim savings only when both runs pass validation; the scorecard intentionally blocks the claim otherwise.
- Record user acceptance and any false-positive intervention separately; absence of feedback is not approval.

## Security and rollback

- Never place `VEILLE_DAEMON_TOKEN`, provider keys, or raw prompts in tickets, screenshots, or fixtures.
- Rotate the project token after an exposure or participant offboarding event.
- Retain encrypted SQLite backups only for the agreed window; verify restore before the pilot begins.
- Stop new uploads, preserve the sanitized evidence, and use the operations runbook for incident response or rollback.

## Readiness criteria

- A pilot is complete only when the owner has reviewed the evidence and documented acceptance or rejection.
- Evidence must include validation, cost, latency, interventions, and the scope/retention decision.
- Submit the checklist and scorecard to the design-partner review before recruiting the next participant.

## Known limits

- VEILLE is a single-host pilot service; it is not HA and does not provide SSO, RBAC, or multi-region replication.
- Model routing, context mutation, and caching remain opt-in and approval-gated.
- Broad production claims require Phase 8 partner evidence, security review, operational SLOs, and explicit workload limits.
