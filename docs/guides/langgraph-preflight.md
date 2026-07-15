# LangGraph preflight integration

Build and approve a VEILLE preflight proposal before invoking a graph. Pass the
resulting session into node closures; each node maps its graph node to a
canonical plan step, reads `session.context_for(step_id)`, and obtains the
approved route with `session.route_for(step_id, capability)`.

Graph node IDs do not need to equal plan step IDs, but the mapping must be
explicit and tested. This keeps context/model changes visible and prevents
hidden rewrites of customer graph logic.

The cited market-research example demonstrates researcher → `research`, analyst
→ `analysis`, and writer → `synthesis`. The feature is opt-in through
`run_scenario(..., apply_preflight=True)`; normal graph execution is unchanged.
