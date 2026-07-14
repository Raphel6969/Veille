"""Phase 4 cache backend port + in-memory and durable (file) implementations."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any, Protocol, cast


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


class FileCacheBackend:
    """Durable, cross-run cache backed by a JSON file on disk.

    Entries persist across Supervisor runs (different ``run_id``s) and are scoped
    by the composite cache key (tenant/project/tool+policy version/auth/context),
    so a shared backend safely serves repeats from *prior* runs. TTL uses wall-clock
    time so expiry is correct across process boundaries. The same ``CachePolicy``
    (exact-only, boundary-scoped, confirmation-gated) governs serving.
    """

    def __init__(
        self,
        cache_dir: str | Path,
        default_ttl_seconds: float = 300.0,
        max_entries: int = 1024,
    ) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "cache.json"
        self._ttl = default_ttl_seconds
        self._max = max_entries
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            return cast("dict[str, dict[str, Any]]", json.loads(self._path.read_text("utf-8")))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(data), encoding="utf-8")

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            data = self._load()
            entry = data.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry["expires_at"] <= now:
                self._misses += 1
                data.pop(key, None)
                self._save(data)
                return None
            self._hits += 1
            return entry["value"]

    def put(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        now = time.time()
        with self._lock:
            data = self._load()
            # Prune expired entries to bound disk usage.
            data = {k: v for k, v in data.items() if v["expires_at"] > now}
            data[key] = {"value": value, "expires_at": now + ttl}
            if len(data) > self._max:
                oldest = min(data, key=lambda k: data[k]["expires_at"])
                data.pop(oldest, None)
            self._save(data)

    def invalidate(self, key: str) -> None:
        with self._lock:
            data = self._load()
            data.pop(key, None)
            self._save(data)

    def stats(self) -> dict[str, int]:
        with self._lock:
            size = len(self._load())
        return {"hits": self._hits, "misses": self._misses, "size": size}


def make_backend(
    kind: str = "memory",
    *,
    cache_dir: str | Path | None = None,
    default_ttl_seconds: float = 300.0,
) -> CacheBackend:
    """Construct a cache backend by kind. ``kind='file'`` requires ``cache_dir``."""
    if kind == "file":
        if cache_dir is None:
            raise ValueError("cache_dir is required for the file backend")
        return FileCacheBackend(cache_dir, default_ttl_seconds=default_ttl_seconds)
    return InMemoryCache(default_ttl_seconds=default_ttl_seconds)
