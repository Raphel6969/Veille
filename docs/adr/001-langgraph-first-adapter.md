# ADR-001: LangGraph as First Framework Adapter

## Status

Accepted — Phase 0

## Context

The Supervisor must integrate with an agent framework without replacing it. The master prompt requires choosing **one** framework deeply for Phase 1: LangGraph or OpenAI Agents SDK.

The first workflow is a multi-step structured research agent (researcher → analyst → writer) with tool calls, retries, and validation—patterns LangGraph handles well.

## Decision

Use **LangGraph** as the first framework adapter.

## Consequences

### Positive

- Strong fit for multi-step research workflows with explicit graph structure
- Durable execution and human-in-the-loop hooks available for Phase 2 pause/resume
- Large production user base among target customers

### Negative

- Teams on OpenAI Agents SDK or CrewAI need to wait for later adapters
- LangGraph API changes require adapter maintenance; version pinned in `pyproject.toml`

## Alternatives considered

| Option | Why not first |
|---|---|
| OpenAI Agents SDK | Simpler but less control over multi-role graph structure |
| CrewAI | Higher integration surface; defer until customer demand |
| Custom code only | Misses framework integration proof point |

## Implementation

- Port: `src/supervisor/adapters/langgraph/port.py`
- Stub: `src/supervisor/adapters/langgraph/stub.py`
- Demo: `examples/cited_market_research/agent.py`
