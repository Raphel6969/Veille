# ADR-010: Semantic dedup and adaptive caching (opt-in, dry-run default)

- **Status:** Accepted (Phase 4)
- **Date:** 2026-07-14

## Context

Phase 4 reduces wasted spend by detecting near-duplicate calls (not just exact
hashes) and serving repeated read-only calls from a cache. Phase 2 already blocks
*exact* duplicate tool calls under enforcement; Phase 4 extends detection to
*semantic* near-duplicates and makes caching a first-class, safe-by-default
optimization. It must not change business outcomes unless explicitly activated,
consistent with Phase 1 observe and Phase 3 advisory.

## Decision

- **Semantic key** (`optimize/keys.py`): `ShingleSemanticKey` tokenizes input
  into word-shingles and compares with Jaccard similarity. Deterministic,
  dependency-free; an embedding backend is a future `SemanticKey` port.
- **Detector** (`optimize/dedup.py`): `DuplicateDetector` indexes in-run
  `(tool, input)` calls and returns `DuplicateMatch` (`exact` | `semantic`,
  `similarity`, `cache_key`). Exact matches use the identical `normalized_input_hash`;
  semantic matches reuse the nearest prior call above `threshold` (default 0.85).
- **Cache** (`optimize/cache.py`): `CacheBackend` port with `InMemoryCache`
  (bounded LRU-ish FIFO + per-entry TTL). Redis is a later backend behind the same
  port. Only **idempotent** calls are cached (`idempotent=False` by default →
  never cached); model calls are cacheable by default (`cacheable=True`) since same
  model+prompt is deterministic.
- **Events** (`contracts/events.py`): schema bumped **0.1.0 → 0.2.0** (additive).
  New `optimization.recommended` (dry-run: a hit *would* have served) and
  `optimization.applied` (active: a hit *was* served). `tool.requested` /
  `model.requested` gain `match_type` + `similarity`. `optimization.*` carry
  `cache_key`, `cache_hit`, `estimated_savings_usd`.
- **Activation** (`SUPERVISOR_OPTIMIZE=1`, sub-mode `SUPERVISOR_OPTIMIZE_MODE`:
  `dry_run` default, `active` to serve). The SDK `Supervisor` reads these; default
  off → behavior identical to Phase 3. Dry-run recommends without executing;
  active serves idempotent cache hits and skips re-execution.
- **Summary** (`analytics/run_summary.py`): `RunSummary` gains `cache_hits`,
  `cache_served`, `semantic_duplicates`, `estimated_savings_usd`.

## Consequences

- Repeated read-only/idempotent calls are served from cache, lowering measured
  cost/latency without changing results.
- Semantic near-duplicates (paraphrased/reordered inputs) are detected, not just
  byte-identical hashes.
- Optimization is safe-by-default: dry-run is observability-only; active is opt-in
  and restricted to idempotent calls; Phase 2 policies still enforce on top.
- Schema 0.2.0 is backward-compatible (additive attributes; 0.1.0 events remain valid).
