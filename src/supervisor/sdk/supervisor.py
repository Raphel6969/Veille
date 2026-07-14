"""Phase 1 Supervisor SDK: typed helpers that emit normalized run events.

The SDK makes an agent run inspectable without changing its business logic.
Application code (or a deeper framework adapter) calls these helpers around
model/tool/context/retry work; the SDK records normalized ``RunEvent`` facts.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from supervisor.context import ContextEngine, ContextManifest
from supervisor.contracts.events import EventType, RunEventBatch
from supervisor.contracts.plan import ExecutionPlan, PlanTier
from supervisor.contracts.task import TaskContract
from supervisor.memory import (
    InMemoryMemoryStore,
    MemoryBackend,
    MemoryGovernor,
    MemoryRecord,
    MemoryTier,
)
from supervisor.optimize import DuplicateDetector, InMemoryCache
from supervisor.optimize.policy import CachePolicy, build_cache_key
from supervisor.planning import Planner
from supervisor.policy.budgets import BudgetTracker
from supervisor.policy.enforcement import Enforcer, GuardDecision, StopRun
from supervisor.policy.engine import DEFAULT_ENFORCE_POLICIES
from supervisor.routing import ModelRouter, RoutingDecision
from supervisor.sdk.collector import RunCollector


def _canonical_text(payload: Any) -> str:
    try:
        return json.dumps(payload, sort_keys=True, default=str)
    except TypeError:  # pragma: no cover - defensive
        return str(payload)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Supervisor:
    """Owns one supervised run: an event collector plus typed emit helpers.

    With ``enforce=True`` the supervisor applies deterministic policy actions
    (block / stop / pause) during execution. With ``enforce=False`` (default)
    it is byte-for-byte identical to Phase 1 observe-only behavior.
    """

    def __init__(
        self,
        task_contract: TaskContract,
        *,
        enforce: bool = False,
        policies: list[Any] | None = None,
        budget: BudgetTracker | None = None,
        optimize: bool | None = None,
        optimize_mode: str | None = None,
        memory: bool | None = None,
        cache_policy: CachePolicy | None = None,
        tenant: str = "default",
        project: str | None = None,
        policy_version: str = "unversioned",
    ) -> None:
        self.task_contract = task_contract
        self.task_id = task_contract.task_id
        self.run_id = str(uuid4())
        self.scenario: str | None = None
        self.enforce = enforce
        self._collector = RunCollector(self.run_id, self.task_id)
        self._enforcer = Enforcer(
            policies if policies is not None else DEFAULT_ENFORCE_POLICIES,
            enforce=enforce,
        )
        self._budget = budget or BudgetTracker(
            cost_limit=task_contract.constraints.max_cost_usd,
            retry_limit=5,
        )
        self._seen_tool_status: dict[tuple[str, str], str] = {}
        self._tool_cache: dict[tuple[str, str], Any] = {}
        self._planner = Planner()
        self._router = ModelRouter()
        self._context_engine = ContextEngine()
        self._plan: ExecutionPlan | None = None
        self._plan_tier: PlanTier | None = None
        # Phase 4: optimization is opt-in (mirrors SUPERVISOR_ENFORCE / SUPERVISOR_PLAN).
        self.optimize = (
            optimize if optimize is not None else os.getenv("SUPERVISOR_OPTIMIZE") == "1"
        )
        mode = optimize_mode if optimize_mode is not None else (
            os.getenv("SUPERVISOR_OPTIMIZE_MODE") or "dry_run"
        )
        self.optimize_mode = mode if self.optimize else "dry_run"
        self._detector = DuplicateDetector()
        # Approved cache policy (v0.2.0 partner-validated rules + confirmation gate).
        self._cache_policy = cache_policy or CachePolicy(
            approved_override=os.getenv("SUPERVISOR_CACHE_APPROVED") == "1",
            partner_confirmations=int(os.getenv("SUPERVISOR_CACHE_CONFIRMATIONS", "0") or 0),
        )
        self._tenant = tenant
        self._project = project or task_contract.task_id or "default"
        self._policy_version = policy_version
        self._cache = InMemoryCache(default_ttl_seconds=self._cache_policy.default_ttl_seconds)
        # Phase 5: memory governance is opt-in (mirrors SUPERVISOR_ENFORCE / PLAN / OPTIMIZE).
        self.memory_enabled = (
            memory if memory is not None else os.getenv("SUPERVISOR_MEMORY") == "1"
        )
        self._memory_backend: MemoryBackend = InMemoryMemoryStore()
        self._memory_governor = MemoryGovernor()

    @property
    def collector(self) -> RunCollector:
        return self._collector

    # -- run lifecycle -----------------------------------------------------

    def start_run(self) -> None:
        attributes: dict[str, Any] = {"task": self.task_contract.task}
        if self.scenario is not None:
            attributes["scenario"] = self.scenario
        if self._plan_tier is not None:
            attributes["tier"] = self._plan_tier.value
        self._collector.emit(EventType.RUN_STARTED, attributes=attributes)

    # -- planning / routing / context -------------------------------------

    def plan(self) -> ExecutionPlan:
        """Build an execution plan (tier + steps) for this run's task contract."""
        self._plan = self._planner.build_plan(self.task_contract)
        self._plan_tier = self._plan.selected_tier
        return self._plan

    def route_model(
        self,
        *,
        step_id: str,
        agent_id: str,
        capability: str,
        allowed_models: list[str] | None = None,
    ) -> RoutingDecision:
        tier = self._plan_tier or PlanTier.BALANCED
        allowed = allowed_models or (
            self.task_contract.constraints.allowed_models or None
        )
        return self._router.select(capability, tier, allowed)

    def finish_run(self, status: str) -> None:
        duplicates = sum(
            1
            for e in self._collector.events()
            if e.event_type == EventType.TOOL_COMPLETED and e.attributes.get("duplicate")
        )
        retries = sum(
            1 for e in self._collector.events() if e.event_type == EventType.RETRY_SCHEDULED
        )
        self._collector.emit(
            EventType.RUN_COMPLETED,
            status=status,
            attributes={"duplicate_search_count": duplicates, "retry_count": retries},
        )

    def emit_validation(self, report: Any) -> None:
        self._collector.emit(
            EventType.VALIDATION_COMPLETED,
            status="pass" if report.task_contract_met else "fail",
            attributes={"checks": [c.model_dump() for c in report.checks]},
        )

    # -- agent / step lifecycle -------------------------------------------

    @contextmanager
    def node(self, *, step_id: str, agent_id: str, role: str) -> Iterator[None]:
        self._collector.emit(
            EventType.AGENT_STARTED,
            step_id=step_id,
            agent_id=agent_id,
            attributes={"role": role},
        )
        try:
            yield
        finally:
            self._collector.emit(
                EventType.AGENT_FINISHED,
                step_id=step_id,
                agent_id=agent_id,
                status="ok",
            )

    # -- model call --------------------------------------------------------

    def model(
        self,
        *,
        step_id: str,
        agent_id: str,
        model: str,
        prompt: str,
        adapter: Any,
        routing: RoutingDecision | None = None,
        cacheable: bool = True,
        auth_scope: str = "default",
        context_boundary: str = "default",
    ) -> str:
        request_attrs: dict[str, Any] = {"prompt_preview": prompt[:120]}
        if routing is not None:
            request_attrs["routing_tier"] = routing.tier.value
            request_attrs["routing_reason"] = routing.reason
            request_attrs["routing_capability"] = routing.capability

        # Phase 4/5 cache policy for model calls (opt-in, approval-gated).
        opt_match = None
        served = False
        cached: dict[str, Any] | None = None
        composite_key: str | None = None
        if self.optimize and cacheable:
            exact_key = _sha256(f"{model}|{prompt}")
            composite_key = build_cache_key(
                f"model:{model}",
                prompt,
                tenant=self._tenant,
                project=self._project,
                tool_version="unversioned",
                policy_version=self._policy_version,
                auth_scope=auth_scope,
                context_boundary=context_boundary,
            )
            opt_match = self._detector.check(f"model:{model}", prompt, exact_key)
            if opt_match is not None:
                request_attrs["match_type"] = opt_match.match_type
                request_attrs["similarity"] = opt_match.similarity
                cached = self._cache.get(composite_key)
                served = (
                    cached is not None
                    and self.optimize_mode == "active"
                    and self._cache_policy.approved
                    and self._cache_policy.is_cacheable_model(model)
                    and self._cache_policy.may_serve(opt_match.match_type)
                )

        self._collector.emit(
            EventType.MODEL_REQUESTED,
            step_id=step_id,
            agent_id=agent_id,
            model_name=model,
            attributes=request_attrs,
        )

        if opt_match is not None and served and cached is not None:
            self._collector.emit(
                EventType.OPTIMIZATION_APPLIED,
                step_id=step_id,
                agent_id=agent_id,
                model_name=model,
                attributes={
                    "cache_key": composite_key or opt_match.cache_key,
                    "match_type": opt_match.match_type,
                    "similarity": opt_match.similarity,
                    "cache_hit": True,
                    "estimated_savings_usd": cached.get("cost_usd", 0.0),
                },
            )
            self._collector.emit(
                EventType.MODEL_COMPLETED,
                step_id=step_id,
                agent_id=agent_id,
                model_name=model,
                duration_ms=cached.get("latency_ms"),
                input_tokens=cached.get("input_tokens"),
                output_tokens=cached.get("output_tokens"),
                cost_usd=0.0,
                status="ok",
            )
            return str(cached["content"])

        result = adapter.complete(model, prompt)

        if (
            self.optimize
            and cacheable
            and self._cache_policy.is_cacheable_model(model)
            and cached is None
            and composite_key is not None
        ):
            self._cache.put(
                composite_key,
                {
                    "content": result.content,
                    "latency_ms": result.latency_ms,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost_usd": result.cost_usd,
                },
                ttl_seconds=self._cache_policy.default_ttl_seconds,
            )
            if opt_match is not None and self.optimize_mode == "dry_run":
                self._collector.emit(
                    EventType.OPTIMIZATION_RECOMMENDED,
                    step_id=step_id,
                    agent_id=agent_id,
                    model_name=model,
                    attributes={
                        "cache_key": composite_key or opt_match.cache_key,
                        "match_type": opt_match.match_type,
                        "similarity": opt_match.similarity,
                        "cache_hit": cached is not None,
                        "estimated_savings_usd": (cached or {}).get("cost_usd", 0.0)
                        if cached is not None
                        else 0.0,
                    },
                )

        self._collector.emit(
            EventType.MODEL_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            model_name=model,
            duration_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            status="ok",
        )
        return str(result.content)

    # -- memory -----------------------------------------------------------

    def remember(
        self,
        *,
        step_id: str,
        agent_id: str,
        content: str,
        tier: MemoryTier = MemoryTier.SHORT,
        confidence: float = 1.0,
        ttl_seconds: float | None = None,
        tenant: str = "default",
    ) -> MemoryRecord:
        """Store a memory record with lifecycle metadata (opt-in)."""
        record = MemoryRecord(
            tenant=tenant,
            content=content,
            tier=tier,
            confidence=confidence,
            ttl_seconds=ttl_seconds,
            provenance={"run_id": self.run_id, "step_id": step_id, "agent_id": agent_id},
        )
        self._memory_backend.store(record)
        return record

    def retrieve_memory(
        self,
        *,
        step_id: str,
        agent_id: str,
        role: str,
        query: str,
        limit: int = 5,
        tenant: str = "default",
    ) -> list[MemoryRecord]:
        """Retrieve governed memories for a step/role (opt-in).

        Emits ``memory.retrieved`` with an inclusion manifest. When memory is
        disabled this is a no-op passthrough (empty retrieval, minimal event).
        """
        if not self.memory_enabled:
            self._collector.emit(
                EventType.MEMORY_RETRIEVED,
                step_id=step_id,
                agent_id=agent_id,
                attributes={"role": role, "included": [], "reason": "memory disabled"},
            )
            return []
        records, manifest = self._memory_governor.retrieve(
            self._memory_backend, query, role, tenant=tenant, limit=limit
        )
        self._collector.emit(
            EventType.MEMORY_RETRIEVED,
            step_id=step_id,
            agent_id=agent_id,
            attributes={
                "role": role,
                "query": query,
                "included": manifest.included,
                "excluded": manifest.excluded,
                "stale": manifest.stale,
                "drift": manifest.drift,
                "scores": manifest.scores,
                "reason": manifest.reason,
            },
        )
        return records

    def expire_memory(self) -> list[MemoryRecord]:
        """Surface memories due for audited removal (never auto-deletes)."""
        if not self.memory_enabled:
            return []
        due = self._memory_governor.expire_due(self._memory_backend)
        for rec in due:
            self._collector.emit(
                EventType.MEMORY_EXPIRED,
                attributes={
                    "memory_id": rec.id,
                    "tier": rec.tier.value,
                    "reason": "ttl_elapsed",
                },
            )
        return due

    def forget_memory(self, memory_id: str) -> None:
        """Explicitly remove a memory (audited). Caller is accountable."""
        self._memory_backend.remove(memory_id)
        self._collector.emit(
            EventType.MEMORY_EXPIRED,
            attributes={"memory_id": memory_id, "reason": "explicit_removal"},
        )

    # -- intervention emission -------------------------------------------

    def emit_intervention(self, decision: GuardDecision) -> None:
        """Record a policy trigger + the applied (or recommended) action."""
        self._collector.emit(
            EventType.POLICY_TRIGGERED,
            step_id=decision.step_id,
            agent_id=decision.agent_id,
            tool_name=decision.tool_name,
            attributes={
                "policy_id": decision.policy_id,
                "mode": decision.mode,
                "action": decision.action,
                "reason": decision.reason,
            },
        )
        self._collector.emit(
            EventType.INTERVENTION_APPLIED,
            step_id=decision.step_id,
            agent_id=decision.agent_id,
            tool_name=decision.tool_name,
            attributes={
                "policy_id": decision.policy_id,
                "mode": decision.mode,
                "action": decision.action,
                "reason": decision.reason,
                "human_review_required": decision.human_review_required,
            },
        )

    def _apply_decision(self, decision: GuardDecision) -> None:
        if decision.action == "observe":
            return
        self.emit_intervention(decision)
        if decision.action == "stop":
            raise StopRun(decision)
        if decision.action == "pause":
            from supervisor.policy.enforcement import PauseForApproval

            raise PauseForApproval(decision)
        # block / warn: handled by the caller without raising.

    def consult(self, policy_id: str, reason: str, **kw: Any) -> GuardDecision:
        """Ask the enforcer whether a detected match should be acted upon."""
        return self._enforcer.decide(policy_id, reason, **kw)

    def act(self, decision: GuardDecision) -> None:
        """Apply a guard decision (emit + optionally interrupt execution)."""
        self._apply_decision(decision)

    # -- tool call ---------------------------------------------------------

    def tool(
        self,
        *,
        step_id: str,
        agent_id: str,
        tool_name: str,
        input: dict[str, Any],
        fn: Callable[[], Any],
        normalized_input_hash: str | None = None,
        duplicate: bool = False,
        failed: bool = False,
        duration_ms: float | None = None,
        cost_usd: float | None = None,
        status: str = "ok",
        error_message: str | None = None,
        idempotent: bool = False,
        tool_version: str = "unversioned",
        auth_scope: str = "default",
        context_boundary: str = "default",
    ) -> Any:
        attributes: dict[str, Any] = {"input": input}
        if duplicate:
            attributes["duplicate"] = True
        if normalized_input_hash is not None:
            attributes["normalized_input_hash"] = normalized_input_hash
            key = (tool_name, normalized_input_hash)
            prior_status = self._seen_tool_status.get(key)
            if prior_status == "ok":
                attributes["duplicate"] = True
                if self.enforce:
                    decision = self._enforcer.decide(
                        "duplicate_tool_protection",
                        "Equivalent successful tool call already deduplicated.",
                        step_id=step_id,
                        agent_id=agent_id,
                        tool_name=tool_name,
                    )
                    if not decision.allow and decision.action == "block":
                        # Dedupe: skip the external call and reuse the cached result.
                        self.emit_intervention(decision)
                        self._collector.emit(
                            EventType.TOOL_REQUESTED,
                            step_id=step_id,
                            agent_id=agent_id,
                            tool_name=tool_name,
                            attributes=attributes,
                        )
                        self._collector.emit(
                            EventType.TOOL_COMPLETED,
                            step_id=step_id,
                            agent_id=agent_id,
                            tool_name=tool_name,
                            status="blocked",
                            attributes=attributes,
                        )
                        return self._tool_cache.get(key)
        if failed:
            attributes["failed"] = True

        # Phase 4/5 cache policy (opt-in). Never changes execution unless the
        # approved policy allows serving an exact, identical-input, cacheable call.
        opt_match = None
        served_from_cache = False
        cached_result: Any = None
        composite_key: str | None = None
        if self.optimize and not failed:
            text = _canonical_text(input)
            exact_key = normalized_input_hash or _sha256(text)
            composite_key = build_cache_key(
                tool_name,
                text,
                tenant=self._tenant,
                project=self._project,
                tool_version=tool_version,
                policy_version=self._policy_version,
                auth_scope=auth_scope,
                context_boundary=context_boundary,
            )
            opt_match = self._detector.check(tool_name, text, exact_key)
            if opt_match is not None:
                attributes["match_type"] = opt_match.match_type
                attributes["similarity"] = opt_match.similarity
                cached_result = self._cache.get(composite_key)
                can_serve = (
                    self.optimize_mode == "active"
                    and self._cache_policy.approved
                    and self._cache_policy.is_cacheable_tool(tool_name)
                    and idempotent
                    and self._cache_policy.may_serve(opt_match.match_type)
                    and cached_result is not None
                )
                if can_serve:
                    served_from_cache = True

        self._collector.emit(
            EventType.TOOL_REQUESTED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            attributes=attributes,
        )

        if served_from_cache and opt_match is not None:
            self._collector.emit(
                EventType.OPTIMIZATION_APPLIED,
                step_id=step_id,
                agent_id=agent_id,
                tool_name=tool_name,
                attributes={
                    "cache_key": composite_key,
                    "match_type": opt_match.match_type,
                    "similarity": opt_match.similarity,
                    "cache_hit": True,
                    "estimated_savings_usd": cost_usd or 0.0,
                },
            )
            self._collector.emit(
                EventType.TOOL_COMPLETED,
                step_id=step_id,
                agent_id=agent_id,
                tool_name=tool_name,
                duration_ms=duration_ms,
                cost_usd=0.0,
                status="ok",
                attributes={**attributes, "cache_hit": True},
            )
            return cached_result

        result = fn()
        resolved_status = "error" if failed else "ok"

        if (
            self.optimize
            and not failed
            and idempotent
            and self._cache_policy.is_cacheable_tool(tool_name)
            and cached_result is None
            and composite_key is not None
        ):
            self._cache.put(
                composite_key, result, ttl_seconds=self._cache_policy.default_ttl_seconds
            )

        if self.optimize and not failed and opt_match is not None:
            if self.optimize_mode == "dry_run":
                self._collector.emit(
                    EventType.OPTIMIZATION_RECOMMENDED,
                    step_id=step_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                        attributes={
                            "cache_key": composite_key or opt_match.cache_key,
                            "match_type": opt_match.match_type,
                            "similarity": opt_match.similarity,
                            "cache_hit": cached_result is not None,
                            "estimated_savings_usd": (cost_usd or 0.0)
                            if cached_result is not None
                            else 0.0,
                        },
                )

        self._collector.emit(
            EventType.TOOL_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            status=resolved_status,
            error_message=error_message if failed else None,
            attributes=attributes,
        )
        self._budget.add_cost(cost_usd)
        if normalized_input_hash is not None and resolved_status == "ok":
            self._seen_tool_status[key] = "ok"
            self._tool_cache[key] = result
        if self.enforce and self._budget.cost_exceeded():
            decision = self._enforcer.decide(
                "cost_budget",
                f"Estimated cost ${self._budget.cost_total():.4f} exceeded budget.",
                step_id=step_id,
                agent_id=agent_id,
                tool_name=tool_name,
            )
            self._apply_decision(decision)
        return result

    # -- retry -------------------------------------------------------------

    def retry(
        self,
        *,
        step_id: str,
        agent_id: str,
        tool_name: str,
        competitor: str,
        attempt: int,
    ) -> None:
        self._budget.record_retry(tool_name)
        if self.enforce and self._budget.retries_exhausted(tool_name):
            decision = self._enforcer.decide(
                "retry_budget",
                f"Retry budget exceeded for {tool_name} (limit {self._budget.retry_limit}).",
                step_id=step_id,
                agent_id=agent_id,
                tool_name=tool_name,
            )
            self._apply_decision(decision)
        self._collector.emit(
            EventType.RETRY_SCHEDULED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            attributes={"competitor": competitor, "attempt": attempt},
        )
        self._collector.emit(
            EventType.RETRY_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            tool_name=tool_name,
            attributes={"competitor": competitor, "attempt": attempt + 1},
        )

    # -- context manifest --------------------------------------------------

    def context(
        self,
        *,
        step_id: str,
        agent_id: str,
        role: str,
        included: list[str] | None = None,
        excluded: list[str] | None = None,
        compressed: list[str] | None = None,
        estimated_tokens: int = 0,
        reason: str = "",
        master_context: list[str] | None = None,
    ) -> None:
        if master_context is not None:
            manifest: ContextManifest = self._context_engine.build_manifest(
                master_context, role, step_id
            )
            included = manifest.included
            excluded = manifest.excluded
            compressed = manifest.compressed
            estimated_tokens = manifest.estimated_tokens
            reason = manifest.reason
        self._collector.emit(
            EventType.CONTEXT_ATTACHED,
            step_id=step_id,
            agent_id=agent_id,
            attributes={
                "role": role,
                "included": included or [],
                "excluded": excluded or [],
                "compressed": compressed or [],
                "estimated_tokens": estimated_tokens,
                "reason": reason,
            },
        )

    # -- batch -------------------------------------------------------------

    def to_batch(self, metadata: dict[str, Any] | None = None) -> RunEventBatch:
        return self._collector.to_batch(metadata=metadata)
