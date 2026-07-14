# Design-partner feedback capture (v0.2.0)

Use this template once per design-partner demo. Run the harness to produce an
objective "observation packet" per scenario, then ask the partner the five
questions below and record their responses. One row per demo.

```markdown
## Demo <ID> — partner: <name> — date: <YYYY-MM-DD> — scenario: <success|expensive|failed_validation> — preset: <baseline|plan|optimize_active|memory|all>

### Q1 — Cost tiers understandable & trusted?
Observed: plan_tier = <...>, total_cost = $<...>, per-model costs = <...>
Partner response (1-5 trust, + why):
- Score (1=confused/untrusted, 5=clear/trusted):
- Notes:

### Q2 — Intervention explanations feel safe?
Observed: interventions_applied = <...>, policies_triggered = <...>, sample reason = "<...>"
Partner response:
- Did the explanation make the action feel safe/justified? (yes / partial / no)
- Notes:

### Q3 — Which repeated tool calls are actually cacheable?
Observed cacheable candidates: <tool xN — exact/semantic>; not flagged: <...>
Partner response:
- Which repeats do YOU consider safe to cache? (list tools + why):
- Which would you NEVER auto-cache? (list + why):
- False-positive risk acceptable? (yes/no + threshold):

### Q4 — Acceptable cache freshness / expiry rules?
Observed defaults: cache TTL = 300s; memory TTL = none; drift excludes, never auto-deletes.
Proposed: idempotent hits served up to 300s; long-tier memory persists with optional TTL; drift excluded.
Partner response:
- Acceptable cache TTL for idempotent results? (e.g., 60s / 300s / 1h / per-session):
- Acceptable memory expiry? (session / days / never / per-TTL):
- Comfortable with never-auto-delete + audited expiry? (yes/no):

### Q5 — Adaptive rerouting welcome, or keep advisory?
Observed: routed calls = <...>; routing is advisory today (annotates, never rewrites).
Partner response:
- Want rerouting enforced automatically? (yes / no / only-with-approval):
- If enforced, what guardrails? (human review / dry-run period / per-agent allowlist):
```

## Aggregation

After 5–10 demos, tally:
- Q1: median trust score; top confusion points.
- Q2: % who felt safe; common safety concerns.
- Q3: consensus cacheable tool set; vetoed tools; agreed false-positive tolerance.
- Q4: consensus cache TTL + memory expiry; unanimity on no-auto-delete.
- Q5: % favoring enforce vs advisory; required guardrails.

## Decision rule (from release plan)

Build **cross-run caching first** only if feedback shows:
- clear, repeated, cacheable work (Q3 consensus on a stable tool set), AND
- safe, agreed freshness/expiry rules (Q4 consensus).
Keep **adaptive rerouting recommendation-only** until enough real outcomes
show it preserves quality.
