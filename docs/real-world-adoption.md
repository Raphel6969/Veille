# Real-world adoption: usage, demo, and testing

How teams actually adopt the supervisor, how we demonstrate it on real workloads,
and how we test it outside the synthetic demo. Written after the v0.2.0 release
and the approved cache policy (ADR-012).

## 1. Usage models (how people plug it in)

The supervisor is a **control plane**, not a replacement runtime. Three adoption
shapes, in order of integration effort:

1. **SDK-embed (lowest friction).** Wrap model/tool calls with
   `Supervisor.tool(...)` / `Supervisor.model(...)`. Works in any Python agent
   (LangChain, raw loop, custom orchestrator). Emits the event stream; nothing
   changes behavior unless flags are on.
2. **Framework adapter (recommended path).** LangGraph adapter already exists
   (callback instrumentation). A lightweight wrapper turns any graph into an
   observed run with zero manual `TraceCapture`. (Haystack, CrewAI, and a generic
   OpenAI-instrumentation adapter are natural next ports.)
3. **Observability bridge (no code change).** Export the event stream to OTel
   (`OtlpExporter`) and onward to Langfuse/Phoenix/LangSmith; use the run-explorer
   CLI for audits. This is the "turn it on beside production" entry point.

All three share the same opt-in safety model: **off by default; observe → enforce
→ plan → optimize → govern memory, each behind its own flag.**

## 2. Real-world demo plan

The synthetic cited-market-research workflow proves wiring but not production
value. A credible real-world demo should:

- **Use a real, read-only, safe external call** (e.g., a public web/search API or
  an internal read-only endpoint) instead of `mock_tools`. No writes, no secrets
  in the repo. This makes cost/savings and cache hits meaningful.
- **Show the five value levers live:**
  - cost-tier + routing annotation (plan),
  - duplicate/near-duplicate detection + cache serve (optimize),
  - memory retrieval manifest (memory),
  - intervention explanations (enforce, dry-run),
  - OTel/run-explorer audit trail.
- **Cache narrative:** run the same query twice; demonstrate `search_competitors`
  served from cache (identical input, approved) with a visible cost delta, and
  show a *different* auth scope / project producing a cache miss (boundary key).
- **Safety narrative:** flip `SUPERVISOR_ENFORCE=true` on a deliberately wasteful
  run and show the run stopped with a human-readable `intervention.applied`.

## 3. Testing strategy for production

- **Golden-trace replay:** capture real (sanitized) runs as fixtures; replay
  through the supervisor and assert the event stream + `RunSummary` are stable
  (regression guard against silent behavior change).
- **Adapter integration tests:** against a sandboxed real tool/LLM (rate-limited,
  mocked at the network boundary) to prove instrumentation under real shapes.
- **Policy/contract tests:** property-based checks that opt-in flags never alter
  business output (the Phase 1 non-interference invariant) across randomized runs.
- **Cache correctness tests:** verify boundary-scoped keys, exact-only serving,
  TTL re-execution, and the confirmation gate (already partly covered in
  `test_cache_policy.py`) against realistic inputs.
- **Canary rollout:** ship advisory-only (plan/observe/optimize dry-run) to a
  tenant; only flip `active`/`enforce` after the confirmation thresholds are met.

## 5. Concrete demo (built): `examples/real_world_demo`

A runnable, safe, offline real-world demo exercising the Supervisor against a
**genuinely read-only HTTP API** (`api.py` starts a local stdlib server serving a
curated competitor dataset; or points at `SUPERVISOR_DEMO_API_URL` if set).

What it demonstrates:

- **Real tool calls** via `Supervisor.tool(...)` (SDK-embed usage model), with a
  real cost model ($0.002/call) so savings are meaningful.
- **Cacheable identical duplicate:** `search_competitors("observability")` is
  called twice; under `SUPERVISOR_OPTIMIZE=1 SUPERVISOR_OPTIMIZE_MODE=active
  SUPERVISOR_CACHE_APPROVED=1` the second is served from cache (cost $0.010 →
  $0.008, `optimization.applied` with `match_type=exact`).
- **Near-duplicate not served:** `search_competitors("observability 2026")` is
  recommended but re-executed (uncertain → re-execute).
- **Boundary-scoped keys:** the composite cache key includes tenant/project,
  tool & policy version, and auth/context — verified by `test_cache_policy.py`.
- **Confirmation gate:** without `SUPERVISOR_CACHE_APPROVED`/`CONFIRMATIONS`, the
  identical duplicate is *not* served even in active mode (cost stays $0.010).

Run it:

```powershell
# observe (all calls execute)
python -m examples.real_world_demo.agent --scenario success

# approved caching (duplicate served, $0.002 saved)
$env:SUPERVISOR_OPTIMIZE=1; $env:SUPERVISOR_OPTIMIZE_MODE=active; $env:SUPERVISOR_CACHE_APPROVED=1
python -m examples.real_world_demo.agent --scenario success
```

Tests: `tests/examples/test_real_world_demo.py` (offline run, cache serve when
approved, gate blocks without confirmation).

### 5.1 Cross-run (durable) caching

The cache backend is pluggable (`supervisor.optimize.cache.CacheBackend`). The
default is an in-memory, per-run `InMemoryCache`; a durable, disk-backed
`FileCacheBackend` (JSON, TTL, tenant-scoped by the composite key) is available,
and `Supervisor` selects it when `SUPERVISOR_CACHE_BACKEND=file` (with
`SUPERVISOR_CACHE_DIR`) or when a backend is passed in code. The same approved
`CachePolicy` (exact-only, boundary-scoped, confirmation-gated) governs serving,
so a cached result is reused across runs/processes **only** for identical inputs
within the same isolation + governance boundary.

The demo exposes this with `--cross-run`:

```powershell
$env:SUPERVISOR_OPTIMIZE=1; $env:SUPERVISOR_OPTIMIZE_MODE=active; $env:SUPERVISOR_CACHE_APPROVED=1
python -m examples.real_world_demo.agent --scenario success --cross-run
# -> run1_cost_usd: 0.008, run2_cost_usd: 0.004, cross_run_saving_usd: 0.004
```

Run 2 serves all three searches from run 1's durable cache (exact-identical
inputs); only the two fetches re-execute. Tests:
`tests/sdk/test_file_cache.py` (backend TTL/expiry, cross-instance read, and
end-to-end cross-run serving via `Supervisor`).

## 4. Open decisions to confirm before building

- **Deployment shape:** self-host library (pip install + OTel) vs a hosted
  control-plane service with a UI? (Affects the enterprise slice we deferred.)
- **First real integration target:** which framework/adapter and which safe
  read-only API should the real-world demo use?
- **Cross-run caching:** the durable `CacheBackend` is now built behind the same
  approved `CachePolicy` (exact-only, boundary-scoped, confirmation-gated). It is
  still *opt-in* and only serves after the confirmation gate is passed; rolling it
  out broadly remains gated on 3–5 partner confirmations (ADR-012). The remaining
  open question is whether the backend should be swappable for Redis at scale.
