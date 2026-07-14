# ADR-012: Approved cache policy (partner-validated rules + confirmation gate)

- **Status:** Accepted (v0.2.0 design-partner feedback)
- **Date:** 2026-07-14

## Context

Phase 4 shipped semantic dedup + caching as opt-in (`SUPERVISOR_OPTIMIZE`), serving
any idempotent call (exact or semantic near-duplicate) from an in-run cache. The
design-partner program surfaced three explicit cache rules the supervisor must
enforce before cross-run caching is safe. This ADR codifies them and adds the
rollout gate the program specified.

## Decision

Implement `supervisor/optimize/policy.py` with `CachePolicy` + `build_cache_key`,
and wire it into `Supervisor.tool()` / `Supervisor.model()`.

**Rule 1 — cacheable only for identical normalized inputs.**
`CachePolicy.require_exact_input=True` (default). Serving requires `match_type ==
"exact"`. Semantic/near-duplicate matches are *recommended* (dry-run) but **never
served** — uncertain results must re-execute. Default `cacheable_tools =
{"search_competitors"}`; only allowlisted, idempotent tools are cached.

**Rule 2 — cache keys include isolation + version + boundary dimensions.**
`build_cache_key(resource, normalized_input, *, tenant, project, tool_version,
policy_version, auth_scope, context_boundary)` produces a composite key
`tenant=…|project=…|resource=…|tool_version=…|policy_version=…|auth=…|ctx=…|input=…`.
A cached result is reused only within the same tenant/project, tool & policy
version, and authorization/context boundary. This prevents cross-tenant/cross-policy
or out-of-scope reuse.

**Rule 3 — freshness gate + re-execute on expiry/uncertainty.**
Default TTL is **300s** (`default_ttl_seconds`). The cache re-executes on TTL
expiry (no stale serve). Combined with Rule 1, semantic/uncertain hits also
re-execute. The 300s default is acceptable **only once partners confirm
freshness is sufficient** (see gate below).

**Rollout gate (partner confirmation).**
`CachePolicy.approved` is `True` only when `approved_override` is set **or**
`partner_confirmations >= require_partner_confirmations` (default **3**). Serving
from cache additionally requires `approved`. Dry-run recommendation is unaffected
(observability only). This encodes: *move forward when at least 3–5 partners
confirm the cacheable unit and freshness policy, with no material stale-result
concern.*

**Adaptive rerouting stays advisory-only** (unchanged from Phase 3/5). It never
rewrites or blocks execution regardless of cache approval.

## Activation

- `SUPERVISOR_OPTIMIZE=1` + `SUPERVISOR_OPTIMIZE_MODE=active` to attempt serving.
- `SUPERVISOR_CACHE_APPROVED=1` (demo/test override) or `SUPERVISOR_CACHE_CONFIRMATIONS=N`
  to satisfy the confirmation gate.
- Programmatic: `Supervisor(..., cache_policy=CachePolicy(partner_confirmations=3))`
  or `CachePolicy(cacheable_tools={...}, approved_override=True)`.

## Consequences

- `search_competitors` repeats with identical normalized input are served from
  cache only after partner confirmation; near-duplicates are never served.
- Cache entries are strictly scoped by tenant/project/version/authorization/context.
- Expired or uncertain results always re-execute — no silent stale serving.
- Cross-run (durable) caching remains a later backend behind `CacheBackend`; the
  same `CachePolicy` + composite key apply when that lands.

## Deferred

- Cross-run durable cache backend (Redis) — same policy/key rules apply.
- Adaptive rerouting enforcement (remains recommendation-only until quality
  outcomes validate it).
