"""Phase 3 model routing: capability + tier fit from a registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from supervisor.adapters.providers import _derive_provider
from supervisor.contracts.plan import PlanTier


@dataclass
class ModelCandidate:
    name: str
    capabilities: list[str]
    tiers: list[PlanTier] = field(default_factory=list)  # empty = suitable for all


@dataclass
class RoutingDecision:
    capability: str
    model: str
    tier: PlanTier
    reason: str
    provider: str | None = None


class ModelRegistry:
    """Maps capabilities to candidate models. Seeded with mock models by default."""

    def __init__(self, candidates: list[ModelCandidate] | None = None) -> None:
        self.candidates = candidates if candidates is not None else self._default()

    def _default(self) -> list[ModelCandidate]:
        all_tiers = list(PlanTier)
        # Mock models come first so the default (no-credential) selection never
        # picks a real provider; real candidates are appended for routing display
        # and opt-in real execution.
        mock = [
            ModelCandidate("mock-research", ["research"], list(all_tiers)),
            ModelCandidate("mock-analysis", ["analysis"], list(all_tiers)),
            ModelCandidate("mock-synthesis", ["synthesis"], list(all_tiers)),
            ModelCandidate("mock-review", ["review"], list(all_tiers)),
        ]
        caps = ["research", "analysis", "synthesis", "review"]
        real = [
            ModelCandidate("gpt-4o", caps, all_tiers),
            ModelCandidate("openrouter/gpt-4o", caps, all_tiers),
            ModelCandidate("claude-3.5-sonnet", caps, all_tiers),
            ModelCandidate("gemini-1.5-pro", caps, all_tiers),
            ModelCandidate("ollama/llama3", caps, all_tiers),
            ModelCandidate("lmstudio/local-model", caps, all_tiers),
        ]
        return mock + real


class ModelRouter:
    """Selects the best-fit model for a capability at a given tier."""

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry()

    def select(
        self,
        capability: str,
        tier: PlanTier,
        allowed_models: list[str] | None = None,
    ) -> RoutingDecision:
        cands = [c for c in self.registry.candidates if capability in c.capabilities]
        if not cands:
            cands = list(self.registry.candidates)  # safe fallback
        tier_match = [c for c in cands if tier in c.tiers]
        pool = tier_match or cands
        if allowed_models:
            filtered = [c for c in pool if c.name in allowed_models]
            pool = filtered or pool
        if not pool:
            return RoutingDecision(
                capability=capability,
                model="mock-research",
                tier=tier,
                reason=(
                    f"No registered model for capability '{capability}'; "
                    f"used static default 'mock-research'."
                ),
            )
        chosen = pool[0]
        reason = f"Selected {chosen.name} for capability '{capability}' at tier {tier.value}."
        if allowed_models:
            reason += " Filtered to allowed_models."
        elif not tier_match:
            reason += " No tier-exact match; used closest available."
        return RoutingDecision(
            capability=capability,
            model=chosen.name,
            tier=tier,
            reason=reason,
            provider=_derive_provider(chosen.name),
        )
