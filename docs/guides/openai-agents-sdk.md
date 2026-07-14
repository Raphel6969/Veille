# OpenAI Agents SDK

Veille includes an adapter for the OpenAI Agents SDK (`openai-agents` package). Currently at **skeleton** status — when the SDK is installed, the adapter routes through the native `Runner` for tracing; otherwise it falls back to the generic instrumented callable.

## Setup

```powershell
pip install openai-agents
```

## Usage

```python
from supervisor.adapters.openai_agents import OpenAIAgentsAdapter
from supervisor.sdk import Supervisor

supervisor = Supervisor(task)
adapter = OpenAIAgentsAdapter()
agent = adapter.attach(my_agent, supervisor)
result = agent.run("user input")
```

## How it works

1. The adapter checks if the `agents` package is importable.
2. If yes, it wraps the agent in a `Runner.run()` call so native tracing is captured.
3. If no, it falls back to `GenericFrameworkAdapter`, which runs the agent callable directly and emits normalized events.
4. Either way, all events flow through the Supervisor SDK with the same contracts, policy checks, and cache rules.

## Registering as a workflow

```python
from supervisor.console.run_registry import register_workflow

register_workflow(
    name="my_oa_agent",
    description="OpenAI Agents SDK workflow",
    framework="openai_agents",
    supports_real=True,
    run_fn=lambda scenario="success", **kw: _run(scenario),
)
```

## Status

**Skeleton** — the adapter structure is in place and the generic fallback works. Full OpenAI Agents SDK tracing integration (handoffs, guardrails, session traces) is planned once the SDK becomes a formal dependency.
