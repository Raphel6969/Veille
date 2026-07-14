from datetime import UTC, datetime, timedelta

from supervisor.memory.scoring import score
from supervisor.memory.store import MemoryRecord, MemoryTier


def _record(**kw) -> MemoryRecord:
    return MemoryRecord(content="c", **kw)


def test_recency_decays_with_age() -> None:
    now = datetime.now(UTC)
    old = _record(last_accessed=now - timedelta(days=30))
    new = _record(last_accessed=now)
    assert score(new, now) > score(old, now)


def test_usage_and_confidence_increase_score() -> None:
    now = datetime.now(UTC)
    low = _record(access_count=0, confidence=0.2)
    high = _record(access_count=5, confidence=1.0)
    assert score(high, now) > score(low, now)


def test_score_is_deterministic() -> None:
    now = datetime.now(UTC)
    rec = _record(access_count=2, confidence=0.8)
    assert score(rec, now) == score(rec, now)


def test_role_weights_nudge_tier_preference() -> None:
    now = datetime.now(UTC)
    working = _record(tier=MemoryTier.WORKING)
    archive = _record(tier=MemoryTier.ARCHIVE)
    weights = {MemoryTier.WORKING: 2.0, MemoryTier.ARCHIVE: 0.5}
    assert score(working, now, weights) > score(archive, now, weights)
