# Phase 5 — Memory lifecycle & governance: Implementation Plan

**Status:** Proposed — approved to begin (Phase 5 discussion gate passed).

**Carried over:** Phases 1–4 are implemented and pushed to `pre_dev`. The runtime now *observes*, *acts*, *plans/contextualizes/routes*, and *optimizes* (semantic dedup + caching). The context engine (Phase 3) already decides per-step context inclusion with reasons; `memory.retrieved` events already exist. Phase 5 adds **long-term memory lifecycle and retrieval governance**: a memory store port, scoring/provenance, stale/drift detection, and a `MemoryGovernor` that decides per step/role *which* memories a step should see — and *why* — without building a vector DB or owning storage. Automatic deletion is explicitly deferred; cleanup is policy-gated and audited only.

**Scope chosen (per discussion):** Workstream A — **Memory lifecycle & retrieval governance** only. Enterprise foundations (tenancy/RBAC/audit/SSO/billing) are deferred to a later sub-phase.

## Goal

For runs that opt in (`SUPERVISOR_MEMORY=1`), the Supervisor:

1. **Stores memories** with tiers (working / short / long / archive), provenance (source run/step), confidence, and TTL.
2. **Scores & retrieves** memories per step/role using recency, usage, provenance, and confidence — not raw similarity alone.
3. **Governs retrieval** — emits a `memory.retrieved` manifest listing included / excluded / stale / drift-flagged memories with explicit reasons and scores.
4. **Cleans up under policy only** — expired/over-quota memories are surfaced for audited removal; the supervisor never silently deletes.
5. **Accounts** for memory use in the run summary (retrieved, stale, drift, expired).

All of this is **opt-in** and **port-backed / mock-first**: the default `InMemoryMemoryStore` needs no external infra; Mem0/Letta/customer RAG are future backends behind the same `MemoryBackend` port.

## Non-goals (explicitly excluded)

- No vector database, embeddings store, or full memory service — storage stays a port; we own scoring/governance.
- No autonomous/automatic deletion — only audited, policy-gated expiry.
- No enterprise foundations this phase: multi-tenancy, RBAC, SSO/SAML/OIDC, billing/quotas, retention/redaction of *run* data, self-host/VPC (integration ports only, deferred).
- No UI; CLI/OTel remain the surface.
- No live provider calls (mock models default).

## User-visible outcome

With `SUPERVISOR_MEMORY=1`:

1. Memory records are stored via `Supervisor.remember(...)` (incl. tier, provenance, confidence, ttl).
2. `Supervisor.retrieve_memory(step_id, agent_id, role, query)` consults `MemoryGovernor`, returns included records, and emits `memory.retrieved` with a manifest (`included`, `excluded`, `stale`, `drift`, `scores`, `reason`).
3. Stale memories (not accessed within `stale_after`) and drift (content/usage changed vs baseline) are flagged in the manifest.
4. `Supervisor.expire_memory()` returns records due for audited removal and emits an `memory.expired`/audit event; nothing is deleted without an explicit, logged action.
5. `RunSummary` reports `memories_retrieved`, `memories_stale`, `memories_drift`, `memories_expired`.

**Safe default:** without `SUPERVISOR_MEMORY`, `retrieve_memory` returns an empty set and emits a minimal `memory.retrieved` (no governance), behavior identical to Phase 4.

## Architecture and design decisions

### D1. Memory store port — `src/supervisor/memory/store.py`

- `MemoryTier` enum: `WORKING`, `SHORT`, `LONG`, `ARCHIVE`.
- `MemoryRecord` (pydantic): `id`, `tenant` (optional, default `default`), `content`, `tier`, `provenance` (run_id/step_id/agent_id), `confidence` (0–1), `created_at`, `last_accessed`, `access_count`, `ttl_seconds` (optional), `baseline_hash` (for drift).
- `MemoryBackend` protocol: `store(record)`, `get(id)`, `retrieve(query, role, limit) -> list[MemoryRecord]`, `record_access(id)`, `due_for_expiry(now) -> list[MemoryRecord]`, `remove(id)`, `stats()`.
- `InMemoryMemoryStore`: default implementation (dict + TTL/quota). No external deps.

### D2. Scoring — `src/supervisor/memory/scoring.py`

- `score(record, now, role_weights) -> float`: combines recency (decay since `last_accessed`), usage (`access_count`), provenance quality, and `confidence`. Deterministic and unit-tested. Role weights nudge tier preference (e.g., `ARCHIVE` preferred for `writer` synthesis context).

### D3. Governor — `src/supervisor/memory/governor.py`

- `MemoryManifest` (pydantic): `included`, `excluded`, `stale`, `drift`, `scores`, `reason` (mirrors `ContextManifest` shape for consistency).
- `MemoryGovernor.retrieve(backend, query, role, *, stale_after, drift_threshold) -> tuple[list[MemoryRecord], MemoryManifest]`:
  - retrieves candidates, scores them;
  - flags `stale` when `now - last_accessed > stale_after` or `confidence < min_confidence`;
  - flags `drift` when current content hash differs from `baseline_hash` beyond `drift_threshold` (usage/confidence drop);
  - includes top-`limit` by score; excludes stale/drift/low-score with reasons.
- `MemoryGovernor.expire_due(backend, now) -> list[MemoryRecord]`: returns due records for audited removal (does not delete).

### D4. Event / summary integration

- Schema remains **0.2.0** (additive attributes on existing `memory.retrieved`; new optional `memory.expired` event type). Document additive.
- `memory.retrieved` attributes extended: `included` (ids), `excluded` (ids), `stale` (ids), `drift` (ids), `scores` (id→score), `reason`, `query`.
- New `EventType.MEMORY_EXPIRED` (audited expiry candidate; never auto-applied).
- `RunSummary` extended: `memories_retrieved`, `memories_stale`, `memories_drift`, `memories_expired`.

### D5. SDK + activation

- `Supervisor(..., memory: bool | None = None)` reads `SUPERVISOR_MEMORY` (default off). When off, `retrieve_memory` returns `[]` and emits a minimal `memory.retrieved`.
- `Supervisor.remember(step_id, agent_id, content, tier=..., confidence=..., ttl_seconds=..., provenance=...)` → stores via backend.
- `Supervisor.retrieve_memory(step_id, agent_id, role, query, limit=...)` → governor retrieval + `memory.retrieved` manifest; returns included records.
- `Supervisor.expire_memory()` → `MemoryGovernor.expire_due` + `memory.expired` events (audited; caller decides removal via `backend.remove`).
- Default backend `InMemoryMemoryStore` (no infra). Future `Mem0Backend`/`LettaBackend` are later ports.

### D6. Safety & defaults

- Opt-in via `SUPERVISOR_MEMORY=1` (mirrors `SUPERVISOR_PLAN` / `SUPERVISOR_OPTIMIZE`).
- No automatic deletion: expiry is surfaced and audited; removal requires an explicit, logged call.
- Memory storage is isolated by `tenant` (default `default`) so future multi-tenancy is a drop-in.
- Safe metadata by default; raw `content` only stored in the backend under the same redaction rules as other payloads.

## Files / components expected to change

| Path | Change |
|---|---|
| `src/supervisor/memory/` (new) | `store.py` (`MemoryBackend`, `InMemoryMemoryStore`, `MemoryRecord`, `MemoryTier`), `scoring.py`, `governor.py`, `__init__.py` |
| `src/supervisor/contracts/events.py` | Add `MEMORY_EXPIRED`; extend `memory.retrieved` attribute registry |
| `src/supervisor/sdk/supervisor.py` | `remember`, `retrieve_memory`, `expire_memory`; `memory` opt-in flag |
| `src/supervisor/analytics/run_summary.py` | `memories_retrieved`, `memories_stale`, `memories_drift`, `memories_expired` |
| `examples/cited_market_research/agent.py` | Optional memory-backed retrieval when `SUPERVISOR_MEMORY` set |
| `tests/memory/`, `tests/sdk/`, `tests/examples/` | New suites |

## Documentation deliverables

- **ADR-011:** Memory lifecycle & governance — store port, scoring, governor, audited expiry (no autonomous deletion).
- `docs/data-contracts.md`: `MemoryRecord`/`MemoryManifest` schema; `memory.retrieved` / `memory.expired` attributes.
- `docs/architecture.md`, `docs/runtime-chain.md`: mark *Memory governance* implemented (opt-in).
- `docs/integrations.md`: `MemoryBackend` port (Mem0/Letta deferred).
- `docs/operations.md`: document `SUPERVISOR_MEMORY`.
- `README.md`, `docs/roadmap.md`, `CHANGELOG.md`: update Phase 5 status after completion.

## Tests and acceptance criteria

- **Store:** put/get/retrieve/record_access; TTL expiry listing; quota behavior; stats; tenant isolation.
- **Scoring:** deterministic; recency/usage/confidence/provenance combine; role weights nudge.
- **Governor:** includes top-scored; excludes low-score; flags stale (recency/confidence); flags drift (hash change); emits manifest with reasons; `expire_due` returns candidates without deleting.
- **SDK integration:** `remember` stores; `retrieve_memory` returns included + emits `memory.retrieved` manifest; `expire_memory` emits `memory.expired` and does not auto-remove; off-mode is a no-op passthrough.
- **Summary:** `RunSummary` includes memory accounting.
- **Safe default:** without `SUPERVISOR_MEMORY`, demo/run output identical to Phase 4.
- **Contract:** events round-trip at 0.2.0; new attributes documented and tested.

**Master-prompt acceptance (Phase 5, memory slice):**

- The supervisor governs *which* memories a step sees and *why*. ✓
- Memory has lifecycle (tiers, scoring, provenance, TTL) and retrieval metrics. ✓
- Stale/drift are detected and surfaced, not silently dropped. ✓
- Cleanup is audited and policy-gated; no autonomous deletion. ✓
- Storage is a port; we own governance, not the vector store. ✓

## Risks, assumptions, dependencies

- **No embeddings by default** — retrieval/scoring is metadata-driven (recency/usage/provenance/confidence); a similarity backend is a future `MemoryBackend`.
- **Governance, not storage** — we deliberately avoid building a memory service; Mem0/Letta are later integrations.
- **Audited expiry only** — automatic deletion deferred per blueprint; Phase 5 surfaces candidates and logs.
- **Compose with earlier phases:** memory governance is additive on top of Phase 3 context + Phase 4 caching; never bypasses enforcement.

---

## Phase 5 approval gate

```
Phase 5 (memory slice) is ready to begin.

Goal: Govern long-term memory lifecycle and retrieval per step/role.

Scope:
  - MemoryBackend port + InMemoryMemoryStore (tiers, provenance, confidence, TTL)
  - Scoring (recency/usage/provenance/confidence) + role weights
  - MemoryGovernor (include/exclude/stale/drift + manifest with reasons)
  - Audited expiry (surface candidates; no autonomous deletion)
  - SDK remember / retrieve_memory / expire_memory (SUPERVISOR_MEMORY opt-in)
  - RunSummary memory accounting

Not in scope:
  - vector DB / embeddings storage (port only)
  - autonomous deletion
  - enterprise: tenancy/RBAC/SSO/billing/retention of run data

Key decisions / assumptions:
  - opt-in via SUPERVISOR_MEMORY (default off)
  - storage is a port; we own scoring/governance
  - expiry is audited, never silent
  - schema stays 0.2.0 (additive memory.retrieved attributes + memory.expired)

Validation:
  - pytest: store, scoring, governor, SDK, summary, safe-default, compose-with-prior
  - ruff + mypy clean
  - demo runs without API keys on Python 3.14

May I implement Phase 5 now?
```
