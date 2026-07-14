from datetime import UTC, datetime, timedelta

from supervisor.memory.store import (
    InMemoryMemoryStore,
    MemoryRecord,
    MemoryTier,
    content_hash,
)


def _record(content: str, **kw) -> MemoryRecord:
    return MemoryRecord(content=content, tier=MemoryTier.SHORT, **kw)


def test_store_and_get() -> None:
    store = InMemoryMemoryStore()
    rec = _record("hello world")
    store.store(rec)
    assert store.get(rec.id) is not None
    assert store.get("missing") is None


def test_retrieve_by_query_and_tenant_isolation() -> None:
    store = InMemoryMemoryStore()
    a = _record("alpha competitor notes", tenant="t1")
    b = _record("beta competitor notes", tenant="t2")
    store.store(a)
    store.store(b)
    assert len(store.retrieve("competitor", "role", tenant="t1")) == 1
    assert len(store.retrieve("competitor", "role", tenant="t2")) == 1
    assert len(store.retrieve("", "role", tenant="t1")) == 1


def test_record_access_updates_metadata() -> None:
    store = InMemoryMemoryStore()
    rec = _record("x")
    store.store(rec)
    before = rec.last_accessed
    store.record_access(rec.id)
    assert rec.access_count == 1
    assert rec.last_accessed >= before


def test_due_for_expiry_respects_ttl() -> None:
    store = InMemoryMemoryStore()
    fresh = _record("fresh", ttl_seconds=3600)
    expired = _record("expired", ttl_seconds=1)
    store.store(fresh)
    store.store(expired)
    now = datetime.now(UTC) + timedelta(seconds=2)
    due = store.due_for_expiry(now)
    ids = {r.id for r in due}
    assert expired.id in ids
    assert fresh.id not in ids


def test_remove() -> None:
    store = InMemoryMemoryStore()
    rec = _record("x")
    store.store(rec)
    store.remove(rec.id)
    assert store.get(rec.id) is None


def test_baseline_hash_set_on_store() -> None:
    rec = _record("payload")
    assert rec.baseline_hash == ""
    InMemoryMemoryStore().store(rec)
    assert rec.baseline_hash == content_hash("payload")
