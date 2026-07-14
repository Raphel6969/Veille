from supervisor.optimize.cache import InMemoryCache


def test_put_then_get() -> None:
    cache = InMemoryCache()
    cache.put("k", "v")
    assert cache.get("k") == "v"
    assert cache.stats()["hits"] == 1


def test_miss_returns_none() -> None:
    cache = InMemoryCache()
    assert cache.get("missing") is None
    assert cache.stats()["misses"] == 1


def test_expired_entry_is_miss() -> None:
    cache = InMemoryCache()
    cache.put("k", "v", ttl_seconds=0)
    assert cache.get("k") is None


def test_lru_eviction() -> None:
    cache = InMemoryCache(max_entries=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)  # evicts oldest ("a")
    assert cache.get("a") is None
    assert cache.get("c") == 3


def test_invalidate() -> None:
    cache = InMemoryCache()
    cache.put("k", "v")
    cache.invalidate("k")
    assert cache.get("k") is None
