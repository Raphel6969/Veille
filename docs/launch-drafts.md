# Launch Drafts

## Hacker News

**Title:** Show HN: Veille – Open-source runtime supervisor for AI agents (plan, govern, verify)

**Body:**

```
pip install veille-supervisor && veille demo

# Then:  veille explore   (timeline, graphs, cache view)
#        veille serve     (web UI at :8010)
#        veille doctor    (health check)
```

Veille is a control plane for production AI-agent work. It wraps any agent (LangGraph, OpenAI SDK, or plain Python) and emits normalized runtime events — model calls, tool calls, context, retries, validation — into a local console with CLI + web UI.

**What it does:**
- **Plan** – tiered execution planning (critical/balanced/efficient)
- **Govern** – deterministic policy enforcement (cost budgets, retry limits, duplicate protection, human review gates)
- **Verify** – validation reports, context manifests, intervention audit trail
- **Optimize** – cross-run cache with approval gates and semantic duplicate detection
- **Memory** – tiered memory with recency/frequency scoring and TTL expiry

**Key design choices:**
- Mock-first by default — no API keys needed to explore
- 8 provider drivers (OpenAI, Anthropic, Gemini, OpenRouter, Ollama, LM Studio, LiteLLM, generic)
- Framework adapters for LangGraph (OpenAI Agents SDK / Responses API coming)
- Type-safe from day one (strict mypy, ruff, 165+ tests)
- One `veille` CLI with 10 subcommands + FastAPI/React web UI

**Stack:** Python 3.12+, FastAPI, React/Vite, LangGraph

Looking for early feedback from anyone running agents in production — especially around the enforcement model, cache policy, and what you'd want from an open-source alternative to AgentOps / LangSmith.

https://github.com/Raphel6969/Veille

---

## Reddit (r/MachineLearning / r/Python)

**Title:** [P] Veille – open-source runtime supervisor for AI agents (pip install & run in 2 min)

**Body:**

Wanted a control plane for agent runs that I could run locally without sending data to a cloud service. Built Veille:

```bash
pip install veille-supervisor
veille demo
veille explore   # CLI timeline
veille serve     # web UI at localhost:8010
```

**What it tracks per run:** model calls, tool calls (with dedup), context attachments, retries, policy interventions, validation results, cost — all normalized into typed event batches that the local console indexes.

**What's different:**
- Mock mode works offline with deterministic costs — explore the full UI with zero API keys
- Policy engine enforces budgets / retry limits / duplicate protection at runtime (opt-in)
- Cross-run cache with confirmation gates (ADR-012)
- 8 provider drivers, framework adapters for LangGraph
- FastAPI backend serves built React UI — `veille serve` and you're done

Would love feedback on the cache policy model and the enforcement API.

https://github.com/Raphel6969/Veille

---

## Twitter/X

**Post 1 (launch):**

```
pip install veille-supervisor && veille demo

Open-source runtime supervisor for AI agents.
Plan → Govern → Verify. All local, no data leaves your machine.

veille explore  (timeline + graphs)
veille serve   (web UI)
veille doctor  (health)

github.com/Raphel6969/Veille
```

**Post 2 (cost tracking):**

```
veille run real_openai_agent --real  # needs OPENAI_API_KEY

Same agent, two modes:
• Mock: deterministic tokens, zero cost
• Real: routes through OpenAIProvider

Cost per call, retry budgets, duplicate savings — all tracked in the event batch.
Open-source, typed, mock-first. pip install veille-supervisor
```

**Post 3 (why):**

```
Every agent run should be inspectable.

Model calls. Tool calls. Context. Retries. Policy interventions. Cost.

Veille wraps any agent and emits normalized events into a local console.
CLI + Web UI + typed SDK. Mock mode by default.

github.com/Raphel6969/Veille
```
