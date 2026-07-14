# Mock demo walkthrough

The mock demo runs a synthetic cited competitor-brief agent through the Supervisor SDK. No API keys, no network, no cost.

```powershell
veille demo mock
```

This executes three scenarios (`success`, `expensive`, `failed_validation`) and prints a summary for each:

```
Run <uuid>  (task cited-competitor-brief-001)
  scenario:         success
  cost:             $0.0138
  latency:          2.09s
  tokens in/out:    150/240
  model calls:      3
  tool calls:       10  (duplicates: 0)
  validation:       pass
```

## What happens

1. The workflow registry loads the `cited_market_research` workflow.
2. The supervisor SDK creates a mock task contract.
3. Three model calls (research, analysis, writing) run through mock provider drivers.
4. Ten tool calls cache results where possible.
5. A validation report checks citation quality.
6. The run summary is printed and saved as a trace fixture.

## Inspecting the result

```powershell
# List saved runs
veille runs

# Explore a specific fixture
veille explore --run fixtures/traces/success_run.json

# Explore with policy annotations
veille explore --run fixtures/traces/expensive_run.json --policy
```

## Live explore

Run a single scenario and inspect it immediately with policy and OTel output:

```powershell
veille explore --live --scenario expensive --policy --otel
```

## Cross-run cache demo

```powershell
veille demo mock --cross-run
```

This enables file-backed caching. The first call for a given (tenant, step, tool, normalized input) seeds the cache; subsequent calls serve the cached result — **only** for identical normalized inputs within the same tenant and policy boundary.
