# ADR-011: Memory lifecycle & retrieval governance

- **Status:** Accepted (Phase 5, memory slice)
- **Date:** 2026-07-14

## Context

Phase 5 adds long-term memory to the supervisor. The blueprint scopes Phase 5
broadly (memory + enterprise), but per discussion we implement only the **memory
lifecycle & retrieval governance** slice this phase. The supervisor must decide
*which* memories a step should see and *why*, without building a vector database
or owning storage. A key blueprint guardrail: **automatic deletion is a later,
explicitly approved capability** — cleanup must be audited, not silent.

## Decision

- **Store port** (`memory/store.py`): `MemoryBackend` protocol with `InMemoryMemoryStore`
  default (no external deps). `MemoryRecord` carries `tier` (working/short/long/archive),
  `provenance` (run/step/agent), `confidence`, `ttl_seconds`, `baseline_hash`, and
  access metadata. Storage is tenant-isolated so future multi-tenancy is a drop-in.
- **Scoring** (`memory/scoring.py`): deterministic `score(record, now, role_weights)`
  combining recency (exponential decay), usage (access count), provenance quality, and
  confidence. No embeddings — metadata-driven; a similarity backend is a future port.
- **Governor** (`memory/governor.py`): `MemoryGovernor.retrieve(...)` returns included
  records + a `MemoryManifest` (included / excluded / stale / drift / scores / reason).
  Flags `stale` (recency/confidence) and `drift` (content hash vs `baseline_hash`);
  excludes stale/drift/low-score with reasons. `expire_due(...)` surfaces TTL-elapsed
  records for **audited** removal and never deletes.
- **Events** (`contracts/events.py`): schema stays **0.2.0** (additive). `memory.retrieved`
  gains `included`/`excluded`/`stale`/`drift`/`scores`/`reason`/`query`; new
  `memory.expired` event records expiry candidates and explicit removals.
- **Activation** (`SUPERVISOR_MEMORY=1`, default off): `Supervisor.remember`,
  `retrieve_memory`, `expire_memory`, `forget_memory`. Off-mode `retrieve_memory` is a
  no-op passthrough. Mirrors `SUPERVISOR_PLAN` / `SUPERVISOR_OPTIMIZE`.
- **Summary** (`analytics/run_summary.py`): `memories_retrieved`, `memories_stale`,
  `memories_drift`, `memories_expired`.

## Consequences

- The supervisor governs memory inclusion per step/role with explicit, auditable reasons.
- Stale/drift memories are surfaced, not silently dropped or auto-deleted.
- Storage remains a port (Mem0/Letta/customer RAG later); we own scoring/governance.
- Opt-in and safe-by-default: off → behavior identical to Phase 4.

## Deferred (explicitly out of scope this phase)

- Enterprise foundations: multi-tenancy enforcement, RBAC, SSO/SAML/OIDC, billing/quotas,
  retention/redaction of *run* data, self-host/VPC.
- Autonomous/automatic deletion — only audited, policy-gated expiry candidates.
- Embedding/similarity memory backends.
