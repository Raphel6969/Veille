# Evidence-Backed Pilot Demo

This is the Phase 8 rehearsal for a permissioned, read-only VEILLE pilot. It demonstrates a proposal, explicit approval, validated execution, and a scorecard. It does not claim customer savings or production readiness.

## Rehearsal

```powershell
veille preflight examples/cited_market_research/task_contract.yaml --output .veille/proposal.json
veille run cited_market_research --proposal .veille/proposal.json --approve --yes
python -m scripts.design_partner_demo --scenario expensive --partner rehearsal
```

Capture the baseline and supervised normalized batches, then calculate the scorecard:

```python
from supervisor.evaluation import scorecard
from supervisor.io import load_trace_fixture

result = scorecard(
    load_trace_fixture("fixtures/traces/expensive_run.json"),
    load_trace_fixture("fixtures/traces/success_run.json"),
)
print(result.as_dict())
```

Use matching task contracts and validation requirements for a real comparison. The fixture command above is a code-path rehearsal only; its scenarios are not interchangeable real-world baselines.

## Claims discipline

- Say that VEILLE produces advisory proposals, requires approval for active application, and records validation-linked evidence.
- Report cost or latency deltas only alongside validation status, intervention counts, and the workload scope.
- Do not call a lower-cost run a success if either run fails validation; `scorecard()` returns zero claimed savings in that case.
