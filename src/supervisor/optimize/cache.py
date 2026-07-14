"""Phase 4 cache backend port + in-memory LRU/TTL implementation."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol


@dataclass
class CacheEntry:
    key: str
    value: Any
    expires_at: float


class CacheBackend(Protocol):
    """Port for a result cache. Implementations may be in-memory or remote."""

    def get(self, key: str) -> Any | None: ...

    def put(self, key: str, value: Any, ttl_seconds: float = 300.0) -> None: ...

    def invalidate(self, key: str) -> None: ...

    def stats(self) -> dict[str, int]: ...


class InMemoryCache:
    """Bounded LRU-ish (FIFO-eviction) cache with per-entry TTL."""

    def __init__(
        self,
        max_entries: int = 128,
        default_ttl_seconds: float = 300.0,
    ) -> None:
        self._max = max_entries
        self._ttl = default_ttl_seconds
        self._store: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        now = monotonic()
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.expires_at <= now:
            self._misses += 1
            self._store.pop(key, None)
            return None
        self._hits += 1
        return entry.value

    def put(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        if key in self._store:
            self._store.pop(key, None)
        elif len(self._store) >= self._max:
            oldest = next(iter(self._store))
            self._store.pop(oldest, None)
        self._store[key] = CacheEntry(key=key, value=value, expires_at=monotonic() + ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def stats(self) -> dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._store)}
