# Current TODO

Last updated: 2026-07-18.

This backlog distinguishes completed repository work from the next product work
and the external release steps. It is intentionally ordered by demo and adoption
impact.

## Completed in the 0.3.3 release candidate

- [x] Package the Console UI and built-in workflow examples in the wheel and sdist.
- [x] Add the missing runtime settings dependency and correct runtime version reporting.
- [x] Build the UI from a clean install in CI.
- [x] Allow scenario selection in the Workflows page.
- [x] Link completed runs to a readable Run Explorer evidence view.
- [x] Verify the UI build, Python checks, package build, and isolated-install smoke test.

## Next: Run Explorer correctness

- [ ] **Sort saved runs newest-first.** In `list_runs`, derive a stable latest-event or
  file-modified timestamp and return runs in descending order; do not rely on filename order.
- [ ] Expose `created_at`, `finished_at`, status, scenario, and total cost in the runs-list API
  so users can identify a run before opening it.
- [ ] Add a regression test that creates multiple traces with different timestamps and asserts
  newest-first ordering in both the registry and `/api/runs`.
- [ ] Add Run Explorer filtering by workflow, scenario, status, and date; add a search field for
  run IDs and task IDs.
- [ ] Preserve the selected run in the URL and make browser back/forward navigation reliable.

## Next: Console UI overhaul

- [ ] Define a small visual system: typography scale, spacing, neutral/color tokens, buttons,
  cards, tables, badges, empty states, loading states, and error states.
- [ ] Replace the current utility-style pages with a polished developer-console layout: compact
  navigation, clear page headers, responsive two-column detail views, and accessible contrast.
- [ ] Redesign Overview as an operational dashboard: latest runs, spend/latency/validation cards,
  active safety mode, and actionable configuration warnings.
- [ ] Redesign Run Explorer as tabs: **Summary**, **Timeline**, **Policies**, **Optimization**, and
  **Validation**; color-code event severity and make the before/after comparison explicit.
- [ ] Improve Workflows with input/schema hints, scenario explanations, run progress, and a clear
  real-mode/confirmation warning before paid execution.
- [ ] Add frontend component tests and one browser-based smoke test for: select scenario → run →
  open evidence → inspect a policy/cache event.

## Demo and launch

- [ ] Rehearse the three-minute story using `cited_market_research: expensive` for detection and
  `real_world_demo: success` with approved exact caching for the safe before/after result.
- [ ] Record the demo only after the Run Explorer ordering and visual pass are complete.
- [ ] Publish `veille-supervisor` **0.3.3** to TestPyPI, perform a clean install test, then publish
  the same version to PyPI. Never upload an already-published version.
- [ ] Configure PyPI Trusted Publishing in GitHub before the release after 0.3.3, replacing manual
  API-token uploads.

## Product boundaries to address later

- [ ] Add declarative workflow manifests / entrypoint discovery for user workflows; never accept
  arbitrary Python uploads to the daemon.
- [ ] Harden and document framework integrations beyond the current LangGraph adapter and generic
  callable wrapper.
- [ ] Add durable production storage, multi-user access controls, retention, and deployment
  guidance before positioning the daemon as a team service.
