"""Run-summary aggregation over a normalized event batch (Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from supervisor.contracts.events import EventType, RunEvent, RunEventBatch


@dataclass
class StepSummary:
    step_id: str
    agent_id: str | None
    model_calls: int = 0
    tool_calls: int = 0
    retries: int = 0
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class ModelSummary:
    model_name: str
    calls: int = 0
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class ToolSummary:
    tool_name: str
    calls: int = 0
    duplicates: int = 0
    cost_usd: float = 0.0


@dataclass
class RunSummary:
    run_id: str
    task_id: str
    scenario: str | None
    total_cost_usd: float
    total_latency_s: float
    total_tokens_in: int
    total_tokens_out: int
    model_calls: int
    tool_calls: int
    retries: int
    duplicates: int
    context_attached: int
    validation_status: str | None
    plan_tier: str | None = None
    routing: list[dict[str, Any]] = field(default_factory=list)
    cache_hits: int = 0
    cache_served: int = 0
    semantic_duplicates: int = 0
    estimated_savings_usd: float = 0.0
    memories_retrieved: int = 0
    memories_stale: int = 0
    memories_drift: int = 0
    memories_expired: int = 0
    per_step: list[StepSummary] = field(default_factory=list)
    per_model: list[ModelSummary] = field(default_factory=list)
    per_tool: list[ToolSummary] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [
            f"Run {self.run_id}  (task {self.task_id})",
            f"  scenario:         {self.scenario}",
            f"  plan tier:       {self.plan_tier}",
            f"  cost:             ${self.total_cost_usd:.4f}",
            f"  latency:          {self.total_latency_s:.2f}s",
            f"  tokens in/out:    {self.total_tokens_in}/{self.total_tokens_out}",
            f"  model calls:      {self.model_calls}",
            f"  tool calls:       {self.tool_calls}  (duplicates: {self.duplicates})",
            f"  retries:          {self.retries}",
            f"  context attached: {self.context_attached}",
            f"  validation:       {self.validation_status}",
            f"  cache hits:       {self.cache_hits} (served: {self.cache_served})",
            f"  semantic dups:    {self.semantic_duplicates}",
            f"  est. savings:     ${self.estimated_savings_usd:.4f}",
            f"  memories:         retrieved={self.memories_retrieved} "
            f"stale={self.memories_stale} drift={self.memories_drift} "
            f"expired={self.memories_expired}",
        ]
        if self.routing:
            lines.append("  routing:")
            for r in self.routing:
                lines.append(
                    f"    - {r.get('capability')}: {r.get('model')} "
                    f"(tier {r.get('tier')})"
                )
        if self.per_step:
            lines.append("  steps:")
            for s in self.per_step:
                lines.append(
                    f"    - {s.step_id} ({s.agent_id}): model={s.model_calls} "
                    f"tool={s.tool_calls} retry={s.retries} cost=${s.cost_usd:.4f}"
                )
        if self.per_model:
            lines.append("  models:")
            for m in self.per_model:
                lines.append(f"    - {m.model_name}: calls={m.calls} cost=${m.cost_usd:.4f}")
        if self.per_tool:
            lines.append("  tools:")
            for t in self.per_tool:
                lines.append(
                    f"    - {t.tool_name}: calls={t.calls} dup={t.duplicates} "
                    f"cost=${t.cost_usd:.4f}"
                )
        return "\n".join(lines)


def _as_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def summarize(batch: RunEventBatch) -> RunSummary:
    events: list[RunEvent] = batch.events
    total_cost = sum(_as_float(e.cost_usd) for e in events)
    tokens_in = sum(int(e.input_tokens or 0) for e in events)
    tokens_out = sum(int(e.output_tokens or 0) for e in events)

    started = next((e for e in events if e.event_type == EventType.RUN_STARTED), None)
    completed = next((e for e in events if e.event_type == EventType.RUN_COMPLETED), None)
    latency = 0.0
    if started is not None and completed is not None:
        delta = (completed.timestamp - started.timestamp).total_seconds()
        latency = max(0.0, delta)

    model_calls = sum(1 for e in events if e.event_type == EventType.MODEL_COMPLETED)
    tool_completes = [e for e in events if e.event_type == EventType.TOOL_COMPLETED]
    tool_calls = len(tool_completes)
    retries = sum(1 for e in events if e.event_type == EventType.RETRY_SCHEDULED)
    duplicates = sum(1 for e in tool_completes if e.attributes.get("duplicate"))
    context_attached = sum(1 for e in events if e.event_type == EventType.CONTEXT_ATTACHED)
    validation = next((e for e in events if e.event_type == EventType.VALIDATION_COMPLETED), None)
    validation_status = validation.status if validation is not None else None

    cache_hits = 0
    semantic_duplicates = 0
    cache_served = 0
    estimated_savings_usd = 0.0
    memories_retrieved = 0
    memories_stale = 0
    memories_drift = 0
    memories_expired = 0
    for e in events:
        if e.event_type in (EventType.TOOL_REQUESTED, EventType.MODEL_REQUESTED):
            if e.attributes.get("match_type"):
                cache_hits += 1
                if e.attributes.get("match_type") == "semantic":
                    semantic_duplicates += 1
        elif e.event_type == EventType.OPTIMIZATION_APPLIED:
            cache_served += 1
            estimated_savings_usd += _as_float(e.attributes.get("estimated_savings_usd"))
        elif e.event_type == EventType.OPTIMIZATION_RECOMMENDED:
            estimated_savings_usd += _as_float(e.attributes.get("estimated_savings_usd"))
        elif e.event_type == EventType.MEMORY_RETRIEVED:
            memories_retrieved += len(e.attributes.get("included") or [])
            memories_stale += len(e.attributes.get("stale") or [])
            memories_drift += len(e.attributes.get("drift") or [])
        elif e.event_type == EventType.MEMORY_EXPIRED:
            memories_expired += 1

    plan_tier = started.attributes.get("tier") if started is not None else None
    routing: list[dict[str, Any]] = []
    for e in events:
        if e.event_type == EventType.MODEL_REQUESTED and e.attributes.get("routing_tier"):
            routing.append(
                {
                    "capability": e.attributes.get("routing_capability"),
                    "model": e.model_name,
                    "tier": e.attributes.get("routing_tier"),
                    "reason": e.attributes.get("routing_reason"),
                }
            )

    steps: dict[str, StepSummary] = {}
    models: dict[str, ModelSummary] = {}
    tools: dict[str, ToolSummary] = {}

    for e in events:
        if e.step_id:
            key = e.step_id
            if key not in steps:
                steps[key] = StepSummary(step_id=e.step_id, agent_id=e.agent_id)
            s = steps[key]
            if e.event_type == EventType.MODEL_COMPLETED:
                s.model_calls += 1
                s.tokens_in += int(e.input_tokens or 0)
                s.tokens_out += int(e.output_tokens or 0)
                s.cost_usd += _as_float(e.cost_usd)
            elif e.event_type == EventType.TOOL_COMPLETED:
                s.tool_calls += 1
                s.cost_usd += _as_float(e.cost_usd)
            elif e.event_type == EventType.RETRY_SCHEDULED:
                s.retries += 1

        if e.event_type == EventType.MODEL_COMPLETED and e.model_name:
            m = models.setdefault(e.model_name, ModelSummary(model_name=e.model_name))
            m.calls += 1
            m.tokens_in += int(e.input_tokens or 0)
            m.tokens_out += int(e.output_tokens or 0)
            m.cost_usd += _as_float(e.cost_usd)

        if e.event_type == EventType.TOOL_COMPLETED and e.tool_name:
            t = tools.setdefault(e.tool_name, ToolSummary(tool_name=e.tool_name))
            t.calls += 1
            t.cost_usd += _as_float(e.cost_usd)
            if e.attributes.get("duplicate"):
                t.duplicates += 1

    return RunSummary(
        run_id=batch.run_id,
        task_id=batch.task_id,
        scenario=batch.metadata.get("scenario"),
        total_cost_usd=round(total_cost, 6),
        total_latency_s=round(latency, 3),
        total_tokens_in=tokens_in,
        total_tokens_out=tokens_out,
        model_calls=model_calls,
        tool_calls=tool_calls,
        retries=retries,
        duplicates=duplicates,
        context_attached=context_attached,
        validation_status=validation_status,
        plan_tier=plan_tier,
        cache_hits=cache_hits,
        cache_served=cache_served,
        semantic_duplicates=semantic_duplicates,
        estimated_savings_usd=round(estimated_savings_usd, 6),
        memories_retrieved=memories_retrieved,
        memories_stale=memories_stale,
        memories_drift=memories_drift,
        memories_expired=memories_expired,
        routing=routing,
        per_step=list(steps.values()),
        per_model=list(models.values()),
        per_tool=list(tools.values()),
    )
