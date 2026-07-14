# Baseline Measurement Report

**Workflow:** Cited market-research (LangGraph)  
**Task contract:** `examples/cited_market_research/task_contract.yaml`  
**Run date:** YYYY-MM-DD  
**Scenario:** success | expensive | failed_validation  
**Supervision:** none (Phase 0 baseline)

## Run identifiers

| Field | Value |
|---|---|
| Run ID | |
| Task ID | cited-competitor-brief-001 |
| Fixture | `fixtures/traces/{scenario}_run.json` |

## Metrics

| Metric | Value | Notes |
|---|---|---|
| Cost (USD) | | Sum of event `cost_usd` |
| Latency (seconds) | | `run.completed` − `run.started` |
| Task success | pass / fail | `ValidationReport.task_contract_met` |
| Validation pass rate | % | Passed checks / total checks |
| Model calls | | Count of `model.completed` |
| Tool calls | | Count of `tool.completed` |
| Duplicate tool calls | | Same tool + `normalized_input_hash` |
| Retries | | Count of `retry.scheduled` |
| Loops detected | | Manual count (Phase 2 automates) |
| Input tokens | | Sum of `input_tokens` |
| Output tokens | | Sum of `output_tokens` |

## Validation checks

| Check | Pass | Message |
|---|---|---|
| required_fields_present | | |
| citations_valid | | |
| no_duplicate_competitors | | |

## Waste patterns observed

| Pattern | Present | Details |
|---|---|---|
| Duplicate search | yes / no | |
| Retry storm | yes / no | |
| Missing citations | yes / no | |
| Budget overrun | yes / no | |

## Comparison slot (Phase 2+)

| Metric | Baseline | Supervised | Delta |
|---|---|---|---|
| Cost (USD) | | | |
| Latency (s) | | | |
| Task success | | | |
| Tool calls | | | |
| Duplicate calls blocked | — | | |

## Notes

- Do not claim optimization success on cost alone.
- Record false positives and policy limitations when supervision is enabled.
- Regenerate fixtures: `python -m examples.cited_market_research.agent --scenario all --write-fixtures`
