# Evaluation and Baselines

## Baseline metrics

| Metric | Definition | Phase 0 source |
|---|---|---|
| Cost (USD) | Sum of `cost_usd` on all run events | Trace fixture metadata |
| Latency (seconds) | Wall-clock from `run.started` to `run.completed` | Event timestamps |
| Task success | `ValidationReport.task_contract_met` | Demo validation |
| Validation pass rate | Passed checks / total checks | Validation report |
| Duplicate tool calls | Tool events sharing tool name + `normalized_input_hash` | Manual count from fixtures |
| Retries | Count of `retry.scheduled` events | Trace fixtures |
| Loops | Exact cycle detections | Manual count (Phase 2 automates) |

## Baseline methodology

> **Baseline credibility (Phase 0):** All baseline metrics in this document are derived from **synthetic** demo runs (`examples/cited_market_research/`). They are reproducible and exercise the measurement framework, but they do **not** yet reflect real production waste. Treat them as illustrative until real or anonymized design-partner traces are added (Phase 0+). The methodology below is designed to be reused unchanged on real traces.

1. Run the synthetic workflow in **success** scenario without supervision.
2. Record metrics using [baseline report template](../templates/baseline_report.md).
3. Repeat for **expensive** and **failed_validation** scenarios.
4. Compare future supervised runs against these baselines.

**Important:** Never claim optimization success based on cost alone. Task success and validation pass rate must remain at or above baseline.

## Quality gates (Phase 0)

| Check | Criterion |
|---|---|
| Required fields | ≥ 8 competitors and non-empty comparison table |
| Citations valid | Every table row has a non-empty `source` |
| No duplicate competitors | Unique competitor names in table |

## Test coverage expectations

| Phase | Tests |
|---|---|
| 0 | Contract round-trip, fixture validation, demo smoke |
| 1 | Event schema compatibility, observe-mode non-interference |
| 2 | Policy intervention fixtures (duplicate, retry, timeout, loop) |
| 3 | Tier recommendations, routing reasons, validation comparison |

## Fixture scenarios

| Fixture | Purpose |
|---|---|
| `success_run.json` | Happy path baseline |
| `expensive_run.json` | Duplicate search + retry storm |
| `failed_validation_run.json` | Missing citations |

Regenerate fixtures:

```powershell
python -m examples.cited_market_research.agent --scenario all --write-fixtures
```
