from supervisor.contracts.plan import PlanTier
from supervisor.routing import ModelCandidate, ModelRegistry, ModelRouter, RoutingDecision


def _registry() -> ModelRegistry:
    return ModelRegistry()


def test_select_returns_default_capable_model() -> None:
    router = ModelRouter(_registry())
    dec = router.select("research", PlanTier.BALANCED)
    assert dec.model == "mock-research"
    assert dec.tier == PlanTier.BALANCED
    assert dec.capability == "research"


def test_select_falls_back_for_unknown_capability() -> None:
    router = ModelRouter(ModelRegistry(candidates=[]))
    dec = router.select("research", PlanTier.BALANCED)
    assert dec.model == "mock-research"  # static default
    assert dec.reason


def test_select_respects_allowed_models() -> None:
    registry = ModelRegistry(
        candidates=[
            ModelCandidate("mock-research", ["research"], list(PlanTier)),
            ModelCandidate("premium-research", ["research"], list(PlanTier)),
        ]
    )
    router = ModelRouter(registry)
    dec = router.select("research", PlanTier.BALANCED, allowed_models=["premium-research"])
    assert dec.model == "premium-research"


def test_select_prefers_tier_specific_entry() -> None:
    registry = ModelRegistry(
        candidates=[
            ModelCandidate(
                "mock-research",
                ["research"],
                [PlanTier.MINIMUM, PlanTier.BALANCED],
            ),
            ModelCandidate(
                "premium-research",
                ["research"],
                [PlanTier.HIGH_QUALITY, PlanTier.MAXIMUM_ASSURANCE],
            ),
        ]
    )
    router = ModelRouter(registry)
    dec = router.select("research", PlanTier.MAXIMUM_ASSURANCE)
    assert dec.model == "premium-research"
    assert dec.tier == PlanTier.MAXIMUM_ASSURANCE


def test_routing_decision_constructs() -> None:
    dec = RoutingDecision(
        capability="research",
        model="mock-research",
        tier=PlanTier.BALANCED,
        reason="static default",
    )
    assert dec.capability == "research"
