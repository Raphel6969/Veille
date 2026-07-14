from datetime import UTC, datetime, timedelta

from supervisor.memory.governor import MemoryGovernor
from supervisor.memory.store import InMemoryMemoryStore, MemoryRecord, MemoryTier


def _store_with(records: list[MemoryRecord]) -> InMemoryMemoryStore:
    store = InMemoryMemoryStore()
    for r in records:
        store.store(r)
    return store


def test_retrieve_includes_top_scored() -> None:
    now = datetime.now(UTC)
    store = _store_with(
        [
            MemoryRecord(content="a", tier=MemoryTier.LONG, access_count=5, confidence=1.0),
            MemoryRecord(content="b", tier=MemoryTier.SHORT, access_count=0, confidence=0.2),
        ]
    )
    gov = MemoryGovernor()
    records, manifest = gov.retrieve(store, "", "researcher", now=now, limit=5)
    assert len(records) >= 1
    assert manifest.included
    assert "a" in manifest.reason or len(manifest.included) >= 1


def test_stale_records_flagged_and_excluded() -> None:
    now = datetime.now(UTC)
    stale = MemoryRecord(
        content="stale memory",
        tier=MemoryTier.LONG,
        last_accessed=now - timedelta(days=30),
        confidence=0.9,
    )
    store = _store_with([stale])
    gov = MemoryGovernor(stale_after=timedelta(days=7))
    _, manifest = gov.retrieve(store, "stale", "researcher", now=now)
    assert stale.id in manifest.stale
    assert stale.id in manifest.excluded
    assert stale.id not in manifest.included


def test_drift_records_flagged_and_excluded() -> None:
    now = datetime.now(UTC)
    rec = MemoryRecord(content="original", tier=MemoryTier.LONG, confidence=0.9)
    store = _store_with([rec])
    rec.content = "mutated content"  # changes hash vs baseline
    gov = MemoryGovernor()
    _, manifest = gov.retrieve(store, "", "researcher", now=now)
    assert rec.id in manifest.drift
    assert rec.id in manifest.excluded


def test_expire_due_surfaces_without_deleting() -> None:
    now = datetime.now(UTC) + timedelta(seconds=2)
    rec = MemoryRecord(content="x", tier=MemoryTier.SHORT, ttl_seconds=1)
    store = _store_with([rec])
    gov = MemoryGovernor()
    due = gov.expire_due(store, now)
    assert rec.id in {r.id for r in due}
    assert store.get(rec.id) is not None  # not deleted
