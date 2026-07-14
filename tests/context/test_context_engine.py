from supervisor.context import ContextEngine, ContextManifest
from supervisor.contracts.task import RiskLevel, TaskContract


def _task() -> TaskContract:
    return TaskContract(
        task_id="t",
        task="demo",
        risk_level=RiskLevel.MEDIUM,
        quality_checks=["citations_valid"],
    )


MASTER = [
    "Research question: define the competitor landscape.",
    "Source list: verified competitor pages with citations.",
    "Audience format notes: executive one-pager.",
    "Constraint: every claim must cite a source.",
]


def test_manifest_includes_role_relevant_slices() -> None:
    manifest = ContextEngine().build_manifest(MASTER, "researcher", "research")
    text = "\n".join(manifest.included).lower()
    assert "research" in text or "source" in text


def test_manifest_excludes_irrelevant_slices() -> None:
    manifest = ContextEngine().build_manifest(MASTER, "researcher", "research")
    joined = "\n".join(manifest.included).lower()
    assert "audience format" not in joined


def test_manifest_tokens_and_compression() -> None:
    manifest = ContextEngine().build_manifest(MASTER, "researcher", "research")
    assert manifest.estimated_tokens > 0
    assert isinstance(manifest.compressed, list)


def test_manifest_deterministic() -> None:
    engine = ContextEngine()
    a = engine.build_manifest(MASTER, "researcher", "research")
    b = engine.build_manifest(MASTER, "researcher", "research")
    assert a.estimated_tokens == b.estimated_tokens
    assert a.included == b.included


def test_manifest_model_constructs() -> None:
    manifest = ContextManifest(step_id="research", role="researcher", included=["x"])
    assert manifest.estimated_tokens == 0
    assert manifest.step_id == "research"
