# Phase 4 — Semantic dedup and adaptive caching: Implementation Plan

**Status:** Proposed — approved to begin (Phase 4 discussion gate passed).

**Carried over:** Phase 1 (observe), Phase 2 (enforcement), and Phase 3 (plan/context/route) are implemented and pushed to `pre_dev`. The runtime can now *observe*, *act*, *plan*, *contextualize*, and *route*. Phase 4 makes the supervisor **reduce waste at runtime**: detect near-duplicate tool/model calls (not just exact hashes) and serve repeated calls from a cache instead of re-executing them. Phase 2 policies remain the safety net on top.

## Goal

During a run, the Supervisor:
1. **Detects near-duplicates** — beyond the exact `normalized_input_hash`, recognize paraphrased / reordered / semantically equivalent tool and model calls within a run (and optionally across runs).
2. **Caches results** — store read-only/idempotent call results behind a cache keyed by a *semantic key*, and serve cache hits to avoid redundant work and spend.
3. **Optimizes safely** — by default in **dry-run** mode it *recommends* optimizations (observes what *would* have been cached/served) without changing execution; when explicitly activated it *serves* from cache. Never caches writes or unsafe tools.

All optimization is **opt-in** (`SUPERVISOR_OPTIMIZE=1`, sub-mode `dry_run` default, `active` to act), mirroring the Phase 1 observe / Phase 3 advisory safety model. Nothing changes the business outcome unless explicitly enabled.

## Non-goals (explicitly excluded)

- No learned/adaptive tier rerouting or cost/latency auto-tune loop (separate Phase 4 workstream, deferred).
- No embedding-API dependency by default — the default near-duplicate detector is a cheap, deterministic similarity (token-shingle + Jaccard / normalized-JSON similarity). An embedding backend is a later, optional port.
- No UI; CLI/OTel remain the surface.
- No live provider calls (mock models default).

## User-visible outcome

Running the demo (or any wrapped agent) with optimization enabled yields:

1. **Semantic duplicate detections** — `tool.requested` / `model.requested` gain a `match_type` (`exact` | `semantic`) and `similarity` on near-duplicate calls.
2. **Cache recommendations (dry-run)** — `optimization.recommended` events listing cache hits that *would* have served, with estimated cost/token savings, while execution proceeds unchanged.
3. **Cache applications (active)** — `optimization.applied` events and the redundant call is served from cache (no re-execution), lowering measured cost/latency.
4. **Run summary accounting** — `RunSummary` gains `cache_hits`, `cache_served`, `semantic_duplicates`, `estimated_savings_usd`.
5. **Safe default:** without opt-in, behavior matches Phase 3 (no caching, no semantic detection emitted).

## Architecture and design decisions

### D1. Semantic key — `src/supervisor/optimize/keys.py`

- `SemanticKey` port: `key(tool_name, normalized_input) -> str`. Default implementation `ShingleSemanticKey` tokenizes the normalized JSON, builds character/prefix shingles, and hashes a sorted shingle set; a `similarity(a, b)` helper computes Jaccard over shingle sets (or normalized-input diff ratio) for thresholding.
- Exact key remains `normalized_input_hash` (Phase 2). The semantic key is a *separate* coarser key used for near-duplicate clustering.
- Embedding backends are a future port (`EmbeddingSemanticKey`) behind the same `SemanticKey` interface; not implemented now.

### D2. Duplicate detector — `src/supervisor/optimize/dedup.py`

- `DuplicateDetector` keeps an in-run index of `(exact_key, semantic_key, tool_name, result_ref)`.
- `check(tool_name, normalized_input) -> DuplicateMatch | None` returns `match_type` (`exact` | `semantic`), `similarity` (0–1), and the prior `result_ref` when a near-duplicate is found within `semantic_threshold` (default 0.85).
- Deterministic and unit-tested; threshold is configurable.

### D3. Cache backend — `src/supervisor/optimize/cache.py`

- `CacheBackend` protocol: `get(key) -> CacheEntry | None`, `put(key, entry, ttl_seconds)`, `invalidate(key)`, `stats()`.
- `InMemoryCache` default: LRU bounded by `max_entries` with per-entry TTL (`ttl_seconds`). Redis-backed implementation deferred behind the same port.
- Only **read-only/idempotent** tools are cached. A tool is cacheable when its call is flagged safe (the SDK `tool()` receives an `idempotent: bool` flag; default `False` → never cached). Model calls are cacheable by prompt similarity when the adapter result is marked safe.

### D4. Event / summary integration

- Schema version bumped **0.1.0 → 0.2.0** (additive, optional attributes; prior 0.1.0 events still valid).
- New event types:
  | Type | Description |
  |---|---|
  | `optimization.recommended` | A cache hit *would* have served (dry-run) |
  | `optimization.applied` | A cache hit *was* served (active) |
- New attributes:
  | Attribute | Type | Emitted on | Meaning |
  |---|---|---|---|
  | `match_type` | string | `tool.requested` / `model.requested` | `exact` \| `semantic` when a near-duplicate is detected |
  | `similarity` | float | `tool.requested` / `model.requested` | Jaccard/diff similarity (0–1) |
  | `cache_key` | string | `optimization.*` | Semantic cache key |
  | `cache_hit` | bool | `optimization.applied` | `true` when served from cache |
  | `estimated_savings_usd` | number | `optimization.*` | Cost avoided by serving from cache |
  | `estimated_savings_tokens` | int | `optimization.*` | Tokens avoided |
- `RunSummary` extended with `cache_hits`, `cache_served`, `semantic_duplicates`, `estimated_savings_usd`.

### D5. Safety & defaults

- Optimization is **opt-in** via `SUPERVISOR_OPTIMIZE=1`; default sub-mode `dry_run` (recommend only), `active` to serve from cache. Set `SUPERVISOR_OPTIMIZE=1 SUPERVISOR_OPTIMIZE_MODE=active` to act.
- Phase 2 policies still enforce on top (a cached/served call still respects cost/retry budgets; caching never bypasses `stop`/`block` decisions).
- Caching is restricted to idempotent tools; writes and unsafe tools are never cached.
- Dry-run is byte-for-byte equivalent to no-optimization execution.

## Files / components expected to change

| Path | Change |
|---|---|
| `src/supervisor/optimize/` (new) | `keys.py` (`SemanticKey`), `dedup.py` (`DuplicateDetector`), `cache.py` (`CacheBackend`, `InMemoryCache`), `__init__.py` |
| `src/supervisor/contracts/events.py` | Add `OPTIMIZATION_RECOMMENDED` / `OPTIMIZATION_APPLIED`; bump `SCHEMA_VERSION` to `0.2.0` |
| `src/supervisor/sdk/supervisor.py` | `tool()` computes exact+semantic key, consults detector/cache; `model()` cacheable by prompt; dry-run/active modes |
| `src/supervisor/analytics/run_summary.py` | `cache_hits`, `cache_served`, `semantic_duplicates`, `estimated_savings_usd` |
| `examples/cited_market_research/agent.py` | Flag idempotent tools; enable optimization wiring when `SUPERVISOR_OPTIMIZE` set |
| `tests/optimize/`, `tests/sdk/`, `tests/examples/` | New suites |

## Documentation deliverables

- **ADR-010:** Semantic dedup + adaptive caching + dry-run opt-in.
- `docs/data-contracts.md`: new event types + attributes; schema 0.2.0 notes.
- `docs/architecture.md`, `docs/runtime-chain.md`: mark *Optimize (cache/dedup)* implemented (opt-in).
- `docs/integrations.md`: cache backend port + semantic key port.
- `docs/operations.md`: document `SUPERVISOR_OPTIMIZE` / `SUPERVISOR_OPTIMIZE_MODE`.
- `README.md`, `docs/roadmap.md`, `CHANGELOG.md`: update Phase 4 status after completion.

## Tests and acceptance criteria

- **Semantic key:** deterministic; similar inputs map to colliding/near keys; dissimilar inputs differ.
- **Detector:** exact match detected; near-duplicate detected above threshold with correct `similarity`; below threshold returns none.
- **Cache backend:** put/get/hit; TTL expiry; LRU eviction; stats.
- **SDK integration:** dry-run emits `optimization.recommended` and still executes; active serves from cache and emits `optimization.applied`; only idempotent tools cached.
- **Summary:** `RunSummary` includes cache/savings accounting; estimated savings match served results.
- **Safe default:** without `SUPERVISOR_OPTIMIZE`, demo output identical to Phase 3.
- **Compose with Phase 2:** cached/served calls still respect budgets; caching never bypasses enforcement.
- **Contract:** event schema round-trips at 0.2.0; new attributes documented and tested.

**Master-prompt acceptance (Phase 4):**

- Near-duplicate tool/model calls are detected, not just exact hashes. ✓
- Repeated read-only calls are served from cache, reducing spend. ✓
- Optimization is safe-by-default (dry-run recommends; active opt-in). ✓
- Cache scope restricted to idempotent/safe calls. ✓
- Trace/event schema contract tests pass at 0.2.0. ✓

## Risks, assumptions, dependencies

- **Similarity heuristic is approximate** — Jaccard over token shingles; tuned via `semantic_threshold`; embedding backend is a future upgrade.
- **Cache correctness depends on idempotency flagging** — only tools explicitly marked idempotent are cached; mislabeled writes would be unsafe (mitigated by default `idempotent=False`).
- **Cross-run caching deferred** — Phase 4 cache is in-run; a durable (Redis) backend is a later port.
- **Compose with enforcement:** caching never bypasses Phase 2 policies.

---

## Phase 4 approval gate

```
Phase 4 is ready to begin.

Goal: Reduce wasted spend by detecting near-duplicates and serving cached results.

Scope:
  - Semantic key (cheap shingle/Jaccard; embedding port later)
  - DuplicateDetector (exact + semantic, threshold)
  - CacheBackend port + InMemoryCache (LRU + TTL, idempotent-only)
  - Event types optimization.recommended / optimization.applied (schema 0.2.0)
  - SDK tool()/model() dry-run + active modes (SUPERVISOR_OPTIMIZE)
  - RunSummary cache/savings accounting
  - Demo idempotent-tool wiring

Not in scope:
  - learned/adaptive tier rerouting or cost-latency auto-tune loop
  - embedding-API dependency by default
  - Next.js control-plane UI

Key decisions / assumptions:
  - opt-in via SUPERVISOR_OPTIMIZE; dry-run default (recommend), active to serve
  - caching restricted to idempotent tools (default False -> never cached)
  - schema 0.2.0 additive; prior 0.1.0 events remain valid
  - Phase 2 policies still enforce on top

Validation:
  - pytest: keys, dedup, cache, SDK dry-run/active, summary, safe-default, compose-with-enforcement
  - ruff + mypy clean
  - demo runs without API keys on Python 3.14

May I implement Phase 4 now?
```
