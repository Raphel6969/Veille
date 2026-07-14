# AI Runtime Supervisor

## Product Blueprint and Phased Build Plan

**Promise:** make AI-agent applications cheaper, faster, safer, and more dependable by supervising how work is planned, contextualized, routed, executed, and verified—without requiring teams to rewrite their application logic.

## 1. What We Are Building

The AI Runtime Supervisor is a control plane for multi-step agent work. It sits between an agent application and model/tool providers, understands the goal of a run, produces an execution plan, monitors work as it happens, and safely intervenes when a run becomes wasteful, stalled, unsafe, or unlikely to meet its requirements.

It is not an agent framework, model provider, or only an API gateway.

| Layer | Core question |
|---|---|
| Agent framework | What steps should the application attempt? |
| Model gateway | Which endpoint can serve this request reliably? |
| Observability platform | What happened during the run? |
| **Runtime Supervisor** | Was this the right plan, context, model, cost, intervention, and final result? |

> Gateways optimize individual requests. The Supervisor optimizes the entire agent execution: intent, plan, context, model selection, cost, progress, and verified outcome.

## 2. Design Principles

1. Integrate with frameworks; do not force a rewrite.
2. Make every recommendation and intervention explainable.
3. Begin in observe mode; enforcement is an explicit policy choice.
4. Prove cost, latency, reliability, and quality impact against a baseline.
5. Fail safely; never silently remove context or stop critical work.
6. Never optimize cost at the expense of an agreed quality guardrail.

## 3. End-to-End Runtime Chain

```text
Agent Request
  ↓
Inspect Request
  ↓
Create / Select Execution Plan
  ↓
Estimate Cost and Latency
  ↓
Optimize and Diversify Context
  ↓
Route Model by Capability Fit
  ↓
Execute and Monitor
  ↓
Detect Problems and Drift
  ↓
Apply Safe Optimizations or Interventions
  ↓
Validate Outcome
  ↓
Return Response, Evidence, and Run Explanation
```

### Task contract

The runtime needs an explicit contract to optimize and validate correctly.

```yaml
task: Produce a cited competitor brief
required_outcome:
  - eight competitors
  - comparison table
  - current linked evidence for material claims
constraints:
  max_cost_usd: 1.00
  max_latency_seconds: 120
  data_residency: EU
quality_checks:
  - required fields present
  - every material claim has a valid source
  - no duplicate competitors
risk_level: medium
```

## 4. Runtime Stages and Features

### A. Inspect request and plan execution

- Classify intent: research, coding, extraction, writing, analysis, review, or workflow automation.
- Detect modalities, constraints, privacy/compliance requirements, output schema, and risk level.
- Decide whether one model call is sufficient or multi-step agent work is required.
- Decompose work into steps, dependencies, roles, expected inputs, and expected outputs.
- Identify independent work that can run in parallel and remove unnecessary agent steps.

### B. Estimate cost and latency

Estimate before the run and again before expensive steps.

- predicted input/output tokens after context construction
- model/provider prices, tool/API fees, planned calls, likely retries, and cache probability
- provider queueing and expected latency
- uncertainty range based on task complexity

```text
Expected cost: $0.38–$0.72
Expected latency: 38–75 seconds
Main driver: evidence synthesis
Cheaper plan: $0.17–$0.31 with lower expected synthesis confidence
```

When a plan exceeds policy, request approval, narrow scope, use an approved cheaper plan, or reject the run.

### Cost options, not only a cost estimate

The runtime should present a recommended plan and meaningful alternatives. A lower-token plan is not automatically the best plan; it may be less reliable for difficult reasoning, code, research synthesis, or high-risk decisions.

| Option | Intended use | Context / token approach | Model and execution approach | What the user receives |
|---|---|---|---|---|
| **Minimum** | Simple, low-risk, well-scoped tasks | Tightest relevant context; lower output budget | Low-cost capable model; minimal steps; safe cache use | Lowest estimated cost and latency, with clearly stated quality limits |
| **Balanced — recommended** | Normal production work | Role-specific relevant context; moderate output and reasoning budget | Best cost-to-validated-quality model plan | Recommended cost, latency, and expected quality range |
| **High quality** | Complex reasoning, important research, difficult code, customer-facing output | Broader verified evidence; more review/validation budget | Higher-performing model for critical steps; optional reviewer pass | Higher expected quality and confidence, with added cost and latency |
| **Maximum assurance** | High-impact, regulated, or irreversible work | Full approved evidence set plus explicit conflict review | Strongest approved model, independent verification, and human approval where required | Highest validation coverage; not necessarily fully automatic |

Example recommendation:

```text
Task: Produce a cited market brief

Minimum:  $0.12–$0.24 | 1,800–3,200 tokens | 20–40 sec
           One research pass, compact context, low-cost synthesis model.
           Suitable for an internal first draft; lower source-coverage confidence.

Balanced: $0.38–$0.72 | 4,000–7,000 tokens | 38–75 sec  ← Recommended
           Role-specific context, specialist research + synthesis steps,
           duplicate-source protection, citation validation.

High quality: $0.90–$1.65 | 8,000–14,000 tokens | 75–150 sec
           Broader evidence, higher-reasoning synthesis model, independent
           reviewer pass, stronger conflict and citation checks.
```

The user, application, or policy can select a tier explicitly. The runtime should also recommend an upgrade when a low-cost plan is unlikely to meet the task contract: for example, "This task requires reconciling conflicting evidence; the Balanced plan is projected to miss the confidence target. Use High quality for an estimated additional $0.73."

When a plan exceeds policy, request approval, narrow scope, select an approved lower tier, or reject the run. Record the selected tier and compare estimated versus actual cost, latency, and validated quality so recommendations improve over time.

### C. Optimize and diversify context

Build a role-specific context manifest rather than sending all information to every agent.

| Role | Include | Exclude |
|---|---|---|
| Researcher | question, source policy, evidence, open questions | UI choices, deployment logs |
| Analyst | verified evidence, rubric, constraints | duplicate pages, stale traces |
| Writer | verified facts, audience, format | tool errors, unused raw context |
| Reviewer | draft, rubric, acceptance criteria | irrelevant implementation history |
| Engineer | requirements, contracts, code/tests | unrelated product discussion |

Capabilities:

- context inventory and token accounting
- relevance scoring and prioritization
- duplicate removal and chunk selection
- role-aware context diversification
- semantic summaries; fact, entity, decision, and constraint extraction
- context expiration, archiving, and versioning
- conflict detection
- explainable inclusion/exclusion/compression records

### D. Route models by capability fit

This is not traffic balancing. Routing is a per-step choice based on required capability and real evaluation evidence.

- reasoning, coding, extraction, vision, language, tool use, structured output
- historical pass rate for this task type and customer evaluation suite
- cost, latency, context-window needs, reliability, and fallback options
- privacy, data residency, and approved-provider policies

```text
Invoice extraction: vision + strict JSON → approved vision model with highest schema-pass rate.
Evidence summary: source preservation + low cost → lower-cost text model.
Conflicting technical evidence: long-context reasoning → higher-reasoning model.
```

Every decision must state why it occurred and its cost/quality tradeoff.

### E. Execute and monitor

Collect normalized events for:

- run, agent, model, tool, retrieval, memory, retry, and policy lifecycle
- tokens, cost, latency, parameters, schema status, and errors
- agent graph, tool timeline, context/memory viewer, live metrics, and replay
- session, project, and tenant budgets

### F. Detect problems and drift

- exact and semantic duplicate tool calls
- retry storms and recurring failure classes
- exact cycles and no-progress loops
- budget/timeout breach risk and stalled tools
- context overflow, duplication, staleness, and conflicts
- output-schema failure and unsupported completion claims
- quality regression and memory drift

### G. Intervene safely

```text
Observe → Warn → Recommend a new plan → Automatically act within policy → Pause for approval → Stop
```

Actions:

- backoff, retry, or provider fallback
- cost/token/time/tool/retry budgets
- block duplicate calls
- compact or replace context only under an approved policy
- reroute to a better-fit model
- skip redundant work or parallelize independent work
- use safe cache results
- hand off to a human or stop while preserving the trace

### H. Validate outcome

Validation ladder:

1. Deterministic: schema, fields, constraints, citations, links, tool results.
2. Domain: calculations, tests, policy rules, writes, or artifact existence.
3. Evaluator: rubric-based assessment only where rules are inadequate.
4. Human review: high-risk or low-confidence outcomes.

Success means reduced cost/latency while validated task-success remains at or above baseline.

## 5. Full Capability Map

| Area | Capabilities |
|---|---|
| Observability | timelines, graphs, tool traces, tokens/costs, replay, health score |
| Protection | loop/retry/timeout protection, budgets, duplicate tools, circuit breakers, human handoff |
| Context | role manifests, scoring, dedupe, chunking, compression, expiry, versioning, conflicts |
| Optimization | estimates, capability routing, token/reasoning budgets, caching, parallelism, convergence |
| Memory | working/short/long/archive tiers, scoring, retrieval metrics, drift, controlled cleanup |
| Quality | acceptance criteria, factual/tool/citation verification, confidence, evaluations, audit |
| Enterprise | tenants, RBAC, SSO, quotas, billing, retention, redaction, audit, self-host/VPC |
| Research | simulation, predictive execution, learned policies, self-healing, swarm/energy optimization |

## 6. Architecture

```text
Agent Application / Framework
          ↓
Supervisor SDK and Framework Adapters
          ↓
Run Controller ── Task Contract + Execution Plan
          ↓
Policy Engine ── Context Engine ── Routing Engine
          ↓
Execution Interceptor / Tool Proxy / Provider Connectors
          ↓
Models, Tools, Retrieval Systems, Memory Stores

All layers emit normalized events
          ↓
Telemetry + Replay Store + Control Plane
          ↓
Run Explorer, Policy Console, Analytics, Audit, Evaluations
```

| Component | Responsibility |
|---|---|
| SDK/adapters | Capture framework events and expose hooks |
| Task-contract service | Goals, constraints, acceptance criteria, risk |
| Run controller | Execution state and intervention coordination |
| Event model | Normalized, replayable run facts |
| Policy engine | Budgets, constraints, and allowed actions |
| Context engine | Assemble, score, diversify, compress, explain |
| Routing engine | Model/tool choice based on capability and policy |
| Validation engine | Required outcome and quality gates |
| Telemetry/replay store | Diagnosis, analysis, and experiments |
| Control plane | Policies, users, projects, environments, audit |

## 7. Build Phases

### Phase 0 — Discovery and baseline (Weeks 1–3)

- Interview 15 teams operating agents in production.
- Obtain anonymized traces/logs from 3–5 prospects.
- Identify repeatable waste: duplicate tools, retries, loops, overruns, failed completion.
- Choose one workflow; start with structured research/document agents.
- Recruit 2–3 design partners for shadow mode.

**Exit:** one paying problem, baseline traces, and a target such as 20% less waste without lower task success.

### Phase 1 — Observe and explain (Weeks 4–8)

- One Python SDK and one framework adapter: LangGraph or OpenAI Agents SDK.
- Normalized event schema, task contract, run timeline, cost breakdown, tool trace, and replay.
- Basic context inventory and observe-only policies.
- Export to existing observability platforms rather than rebuilding them.

**Exit:** partner can identify why a run was slow, expensive, or unsuccessful.

### Phase 2 — Deterministic protection (Weeks 9–14)

- Cost/token/time/tool/retry budgets.
- Duplicate tool input hashes and exact cycle detection.
- Failure classification, backoff, and intervention modes.
- Clear explanations, approval, and human-review handoff.

**Exit:** low false-positive waste detection; one partner enables a low-risk enforcement rule.

### Phase 3 — Planner, context, and routing (Weeks 15–22)

- Pre-flight cost/latency estimate and simple execution-plan representation.
- Role-aware manifests, deduplication, relevance scoring, compression recommendations.
- Capability registry for 2–3 approved models and explainable routing.
- Deterministic output validation for the first workflow.

**Exit:** measured efficiency gain with task success and validation at baseline or better.

### Phase 4 — Adaptive optimization (Months 6–9)

- Semantic duplicate/no-progress detection.
- Policy-controlled compression and role-aware context injection.
- Quality-aware fallback/routing, safe caching, parallelism, scheduling, and experiments.

**Exit:** repeatable 15–30% efficiency improvement with documented quality guardrails.

### Phase 5 — Memory and enterprise (Months 9–15)

- Memory quality/lifecycle controls.
- Multi-tenancy, RBAC, audit, billing, quotas, SSO, redaction, retention, self-host/VPC.
- Add integrations only where customer demand proves value.

**Exit:** paid annual enterprise deployments and repeatable security review.

### Phase 6 — Learning and simulation (After product-market fit)

- Historical trace simulation, predictive success/cost/latency, learned policy recommendations.
- Safe workflow repair, advanced multi-agent scheduling, energy-aware execution.

## 8. First Product Scope

Build a **Runtime Supervisor for structured research agents**:

- task contract
- trace and replay
- pre-flight cost estimate
- time/cost/retry/tool budgets
- duplicate tool-call and exact-loop detection
- context-manifest recommendations
- capability routing across 2–3 approved models
- required-source and structured-output validation
- human-readable policy and intervention explanation

Do not begin with a replacement framework, standalone observability product, all providers/languages, autonomous memory deletion, learned optimization, or enterprise billing/SSO.

## 9. Success Metrics

| Category | Metrics |
|---|---|
| Adoption | active projects, protected runs, policy enablement |
| Efficiency | cost/tokens/latency/tool calls per run, cache hit rate |
| Reliability | retries, failures, stalled runs, loop rate |
| Quality | task success, validation passes, evaluator score, human acceptance |
| Safety | false/overridden interventions, policy violations |
| Business | pilot-to-paid conversion, savings shown, retention |

## 10. Immediate Next Actions

1. Select the first workflow and framework.
2. Define the task-contract and normalized event schemas.
3. Recruit three design partners and gather representative traces.
4. Build a shadow-mode SDK and run explorer.
5. Add four deterministic policies: cost budget, timeout, retry budget, duplicate tool call.
6. Agree on success baseline and quality checks with each partner.
7. Run a measured pilot before adding autonomous optimization.

## 11. Competitor Map and Differentiation Strategy

The product should not attempt to replace every adjacent category. For each runtime stage, choose deliberately whether to **integrate**, **complement**, or **compete**.

### 11.1 Inspect request and create an execution plan

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| LangGraph | Durable, stateful agent orchestration; persistence and human-in-the-loop | Integrate first through an adapter | Cross-framework planning quality: analyze the task contract, choose a plan, estimate it, and intervene across the entire run |
| CrewAI | Multi-agent crews and flows, including memory, guardrails, state, and observability | Integrate through callbacks/hooks | Framework-neutral plan analysis and policy enforcement; work for CrewAI, LangGraph, OpenAI Agents SDK, and custom code |
| Temporal / durable workflow engines | Reliable workflow execution, retries, state, and scheduling | Integrate for durable execution customers | AI-aware decisions: token cost, context usefulness, model fit, tool duplication, and output quality |

**Do not compete first:** building a new graph/orchestration framework. The Supervisor should enrich existing workflows with an execution plan, task contract, and policy layer.

### 11.2 Estimate cost and latency

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| LiteLLM | Unified access to many models, spend tracking, budgets, fallback, and routing | Integrate as a provider/gateway connector | Forecast the cost of the entire plan before execution, including context, tools, retries, and expected number of steps |
| Portkey / Helicone | Gateway controls including cost logging, caching, fallbacks, rate limits, and provider operations | Integrate where already deployed | Compare alternative *execution plans*, not merely alternate API endpoints; recommend scope reduction or a different agent plan before cost is incurred |
| Cloud provider cost tools | Report model usage and spend | Ingest as a source of truth | Per-task cost-to-quality attribution and an explainable estimated-versus-actual variance report |

**Own:** plan-level cost/latency forecasting, uncertainty ranges, and policy actions tied to the actual task outcome.

### 11.3 Optimize and diversify context

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| Letta | Stateful agents with memory blocks, files, archival memory, and agent-controlled context | Integrate through memory/context adapters | A runtime-generated context manifest for every role and step, including explicit reasons for inclusion, exclusion, compression, and confidentiality boundaries |
| Mem0 | Managed and open-source memory layer with entity-scoped memory, graph memory, retrieval, and lifecycle controls | Integrate as an optional memory provider | Cross-agent, goal-aware context diversification: send different verified slices of a shared master context to researcher, analyst, writer, reviewer, and engineer roles |
| RAG/vector databases | Retrieval, chunking, filters, reranking | Integrate via retrieval events and connectors | Measure whether retrieved information was actually used, wasted, stale, contradictory, or responsible for a quality regression |

**Own:** the policy and evidence layer that decides what information a given step should see. Do not compete first by building a vector database or a full memory store.

### 11.4 Route a model by capability fit

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| LiteLLM / Portkey | Provider abstraction, traffic routing, fallback, load balancing, rate limits, and cost controls | Use as the reliable execution path | Capability-aware selection based on the step's requirements, customer evaluation results, model quality, privacy policy, cost, latency, and fallback risk |
| Model provider routers | Choose among a provider's own deployments/models | Use as a downstream option | Cross-provider, task-specific routing with an auditable reason and measured expected-quality tradeoff |
| Model benchmark sites | Publish general-purpose scores | Use as initial priors only | Customer-specific model scorecards from real task contracts and validated outcomes |

**Own:** the model policy: "for this step, under these constraints, this model gives the best expected validated result." Gateway health and load balancing remain integration concerns.

### 11.5 Monitor execution and provide replay

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| Langfuse | Open-source tracing, prompts, evaluation, datasets, and experiments | Send normalized traces to it or ingest its data | Explain which supervisor decision changed the run and quantify the resulting cost, latency, and quality impact |
| LangSmith | Tracing, agent observability, evaluation, deployment, and human feedback workflows | Provide native trace links/export | Cross-framework run-health score and a decision ledger spanning agents, models, context, tools, and policies |
| Arize Phoenix | OpenTelemetry-based tracing, evaluation, prompt iteration, replay, datasets, and experiments | Make OpenTelemetry a first-class integration | Move from post-hoc diagnosis to live, policy-controlled intervention at the trajectory level |

**Do not compete first:** a separate telemetry storage system or generic trace UI. Emit and ingest OpenTelemetry; make the product's primary view the *decision and intervention timeline*.

### 11.6 Detect problems and apply interventions

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| LangGraph human-in-the-loop | Pause named tool calls for approve/edit/reject decisions | Integrate with the framework's pause/resume mechanism | Detect when intervention is needed from run-level evidence: no progress, repeated action, cost trajectory, context conflict, or failed acceptance criteria |
| Guardrail products and provider guardrails | Screen inputs/outputs for safety, policy, or format violations | Integrate selected guardrails as policy checks | Multi-step trajectory policies that reason over the run, not only one input/output pair |
| Patronus AI | Evaluation, monitoring, agent debugging, and real-time evaluator-based guardrails | Integrate evaluators for checks that cannot be deterministic | Policy actions that combine evaluator results with budget, plan state, tool history, and human escalation rules |

**Own:** explainable, cross-step intervention. Start with deterministic policies: budget, timeout, retry limit, duplicate input hash, and exact loop. Add semantic no-progress detection only after gathering real traces.

### 11.7 Validate final output and learn from outcomes

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| LangSmith / Phoenix | Datasets, experiments, online/offline evaluation, annotations, trace replay | Export results and reuse existing evaluation workflows | Bind validation directly to the task contract and compare baseline execution against optimized execution |
| Patronus AI | Prebuilt and custom evaluators, production monitoring, live guardrails | Use specialty evaluators where appropriate | Treat validation results as signals for routing, context, planning, and intervention—not only as a dashboard score |
| Test frameworks and domain validators | Deterministic schema, code, calculation, and artifact checks | Integrate and prioritize them | A unified acceptance-criteria engine that decides whether the agent may claim completion |

**Own:** task-success governance. The key question is not merely "was the output good?" but "did the optimized run still achieve the contracted outcome at least as well as baseline?"

### 11.8 Memory intelligence

| Competitors / adjacent products | What they do | Recommended approach | Differentiation to own |
|---|---|---|---|
| Letta | Agent-managed persistent in-context and archival memory; shared blocks | Integrate where a customer already uses it | Runtime memory-use audit: did a memory improve this step, was it stale, and should it be included for this role? |
| Mem0 | User/agent/session memory, retrieval, graph memory, filters, and retention | Integrate as a memory backend | Policy-controlled memory lifecycle with confidence, recency, usage, provenance, and validation outcomes |

**Own:** memory quality and use governance, not storage. Automatic deletion must be a later, explicitly approved capability.

## 12. Integration-First Product Stack

Start with this composition rather than rebuilding mature infrastructure.

```text
Customer's Framework: LangGraph / CrewAI / OpenAI Agents SDK / custom
                 ↓
AI Runtime Supervisor: task contract, plan, context manifest, policy,
                       capability routing, intervention, validation ledger
                 ↓
Gateway Connector: LiteLLM / Portkey / direct providers
                 ↓
Memory Connector: Mem0 / Letta / customer's RAG or database
                 ↓
Observability Connector: OpenTelemetry → Langfuse / Phoenix / LangSmith
                 ↓
Evaluator Connector: deterministic checks + Patronus / customer's evaluators
```

This lets a customer retain their existing stack and adopt the Supervisor first in shadow mode. It also prevents the product from becoming a risky, all-or-nothing platform migration.

## 13. Competitive Moat to Build

The durable advantage is not a model proxy, a trace viewer, or a single loop detector. It is a proprietary, customer-specific execution dataset that connects:

```text
Task contract
→ execution plan
→ context chosen for each role
→ model/tool choices
→ interventions
→ validated outcome
→ actual cost and latency
```

Over time, that dataset supports better forecasts, routing, context policies, simulation, and recommendations. Build it only with customer controls, clear data boundaries, and opt-in learning policies.

## Positioning

> **AI Runtime Supervisor is the control plane for production agent work. It plans, contextualizes, routes, governs, and verifies each agent run—reducing wasted spend and unreliable outcomes without requiring teams to rebuild their applications.**

## 14. How to Showcase the Product

Do not lead with a generic dashboard or the phrase "Kubernetes for agents." Show one memorable **before-versus-after supervised run**.

### Demo story: a cited market-research agent

1. **Define the task contract** — request a cited competitor brief with a $1 budget, two-minute deadline, and source-validation requirement.
2. **Show the execution choices before spending** — display Minimum, Balanced, and High Quality options with token, cost, latency, and validation trade-offs. Select Balanced.
3. **Show role-aware context** — researcher receives sources and open questions; analyst receives verified evidence; writer receives approved facts. Make excluded/stale context visible.
4. **Run the agent live** — show the plan, agent/tool timeline, cost meter, and context/model choices as they happen.
5. **Demonstrate one supervised intervention** — the agent repeats a search or exceeds a tool budget; the Supervisor identifies it, blocks the duplicate call, explains why, and continues safely.
6. **Validate the result** — show cited-output checks, required fields, total actual cost/latency, and a clear task-contract pass/fail result.
7. **Reveal the comparison** — show a baseline run beside the supervised run: tool calls avoided, tokens/cost saved, latency change, and validation outcome.

The demonstration should make this promise concrete:

> "We did not alter the agent's business logic. We made one run cheaper, more controlled, and demonstrably complete."

### Recommended showcase assets

| Asset | Purpose |
|---|---|
| Interactive demo | Let prospects change budget/quality tier and observe an execution-plan recommendation |
| Three-minute product video | Tell the before → intervention → validated-after story without requiring setup |
| Public demo repository | One runnable agent, synthetic tools/data, shadow and enforce modes, reproducible fixtures |
| One-page technical architecture | Explain integration points and data boundaries to technical buyers |
| Savings/reliability report | Quantify costs avoided, duplicate calls blocked, validation rate, and false interventions |
| Design-partner case study | Prove value in a real workflow once a pilot is complete |

Avoid showcasing autonomous optimization until it has been proven safe. In an early demo, deterministic duplicate-call and budget protection are more trustworthy than a vaguely "intelligent" intervention.

## 15. Recommended Technical Stack

### MVP stack — deliberately small

| Layer | Recommendation | Why |
|---|---|---|
| Primary language | Python 3.12+ | Strong agent/framework ecosystem and fast SDK development |
| API / control plane | FastAPI + Pydantic | Typed task/policy/event contracts and automatic API documentation |
| First agent adapter | LangGraph **or** OpenAI Agents SDK | Choose only one based on the first design partner; do not support both deeply on day one |
| Model access | LiteLLM adapter plus direct provider adapter | Provider abstraction, pricing metadata, fallback, and customer flexibility |
| Runtime core | In-process Python library first | Lowest-friction integration and easiest shadow-mode adoption |
| Normalized telemetry | OpenTelemetry + GenAI semantic conventions where applicable | Open ecosystem integration and portable trace/event boundaries |
| System of record | PostgreSQL | Task contracts, policies, users, projects, run metadata, audit data |
| Short-lived state | Redis | Budgets, idempotency keys, counters, rate windows, job coordination |
| Replay/artifacts | S3-compatible object storage (MinIO locally) | Store redacted payloads, large traces, and test artifacts with retention control |
| Background work | Simple worker queue initially (e.g. Celery/Arq/Dramatiq) | Run aggregation and non-blocking analysis without premature workflow complexity |
| Web app | Next.js + TypeScript + Tailwind CSS | Fast control-plane UX and a strong ecosystem for developer tools |
| Graph/timeline UX | React Flow plus a timeline/chart library | Agent-plan graph, tool timeline, and intervention visualization |
| Testing | pytest, contract tests, Playwright for critical UI flows | Reliable core policy behavior and end-to-end demo confidence |
| Local environment | Docker Compose | Reproducible developer and demo setup |
| CI | GitHub Actions | Lint, type checks, tests, schema checks, and documentation validation |

### Add later, only when demand proves it

| Capability | Add when | Recommendation |
|---|---|---|
| High-volume analytics | You have many tenants/runs and dashboard queries strain Postgres | ClickHouse for append-heavy event analytics |
| Durable multi-day execution | Runs must survive outages or pause for long human approval | Temporal or the chosen framework's durable execution features |
| Vector / memory storage | A customer needs external retrieval/memory at scale | Integrate Mem0, Letta, or customer-owned retrieval infrastructure |
| Enterprise identity | First enterprise deal requires it | OIDC/SAML provider and RBAC layer |
| Self-hosting/VPC | Security reviews or data residency require it | Helm/Kubernetes deployment only after core product maturity |

### Architecture rules for the stack

- Use Postgres first; do not add ClickHouse, a vector database, and Temporal to the first prototype merely because the future platform may need them.
- Keep the Supervisor's data contracts independent of LiteLLM, LangGraph, or any observability vendor.
- Emit standard telemetry, but keep a Supervisor-specific decision/intervention record because generic traces do not capture the full policy rationale.
- Store raw prompts/tool payloads only behind explicit retention/redaction controls; use safe metadata by default.
- Feature-flag every policy, context transformation, router, and enforcement action.

OpenTelemetry provides common semantic attributes for traces, metrics, logs, and GenAI-related telemetry, making it a strong portability foundation. [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/), [GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai)  
ClickHouse is appropriate later for high-throughput real-time analytics and observability workloads, not a requirement for the earliest MVP. [ClickHouse observability use case](https://clickhouse.com/use-cases?log=use-case-observability)  
Temporal is a later option for long-running, crash-resilient workflows; its durable execution model resumes work after failures, but it adds operational complexity that the initial shadow-mode SDK does not need. [Temporal documentation](https://docs.temporal.io/)
