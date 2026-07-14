# Product and Technical Assumptions Register

## Phase 0 assumptions

| ID | Assumption | Owner | Validate by |
|---|---|---|---|
| A-001 | Cited market-research is the right first workflow | Product | Design partner feedback (Phase 0+) |
| A-002 | LangGraph is the right first adapter | Engineering | Phase 1 instrumentation success |
| A-003 | Synthetic traces are sufficient for Phase 0–1 | Engineering | Compare with real traces when available |
| A-004 | Mock model costs are adequate for baseline demos | Engineering | Phase 1 real pricing integration |
| A-005 | Observe-first policies build customer trust | Product | Phase 2 partner pilot |
| A-006 | Postgres + Redis + MinIO scaffold meets Phase 1 needs | Engineering | Phase 1 persistence requirements |

## Technical constraints

- Python 3.12+ only for Phase 0–1 SDK
- No paid API calls in default CI or quickstart path
- All policies start in `observe` mode
- Documentation updated with every meaningful code change

## Open questions (not blocking Phase 0)

| Question | Impact | Target phase |
|---|---|---|
| Which OTel backend first? | Export format priorities | Phase 1 |
| Minimum viable run explorer: CLI vs API? | UX scope | Phase 1 |
| Real design partner traces available? | Baseline accuracy | Phase 0+ ongoing |
