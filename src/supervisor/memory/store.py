"""Phase 5 memory store port + in-memory implementation (mock-first)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MemoryTier(StrEnum):
    WORKING = "working"
    SHORT = "short"
    LONG = "long"
    ARCHIVE = "archive"


class MemoryRecord(BaseModel):
    """A single memory with lifecycle metadata for governance."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant: str = "default"
    content: str
    tier: MemoryTier = MemoryTier.SHORT
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=_now)
    last_accessed: datetime = Field(default_factory=_now)
    access_count: int = 0
    ttl_seconds: float | None = None
    baseline_hash: str = ""

    def content_hash_now(self) -> str:
        return content_hash(self.content)


class MemoryBackend(Protocol):
    """Port for memory storage. Future backends: Mem0 / Letta / customer RAG."""

    def store(self, record: MemoryRecord) -> None: ...

    def get(self, record_id: str) -> MemoryRecord | None: ...

    def retrieve(self, query: str, role: str, tenant: str = "default") -> list[MemoryRecord]: ...

    def record_access(self, record_id: str) -> None: ...

    def due_for_expiry(self, now: datetime | None = None) -> list[MemoryRecord]: ...

    def remove(self, record_id: str) -> None: ...

    def stats(self) -> dict[str, Any]: ...


class InMemoryMemoryStore:
    """Default memory backend. No external dependencies; tenant-isolated."""

    def __init__(self) -> None:
        self._store: dict[str, MemoryRecord] = {}

    def store(self, record: MemoryRecord) -> None:
        if not record.baseline_hash:
            record.baseline_hash = record.content_hash_now()
        self._store[record.id] = record

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._store.get(record_id)

    def retrieve(self, query: str, role: str, tenant: str = "default") -> list[MemoryRecord]:
        candidates = [r for r in self._store.values() if r.tenant == tenant]
        if not query:
            return list(candidates)
        q = query.lower()
        return [r for r in candidates if q in r.content.lower()]

    def record_access(self, record_id: str) -> None:
        rec = self._store.get(record_id)
        if rec is None:
            return
        rec.last_accessed = _now()
        rec.access_count += 1

    def due_for_expiry(self, now: datetime | None = None) -> list[MemoryRecord]:
        now = now or _now()
        due: list[MemoryRecord] = []
        for rec in self._store.values():
            if rec.ttl_seconds is None:
                continue
            if (rec.created_at.timestamp() + rec.ttl_seconds) <= now.timestamp():
                due.append(rec)
        return due

    def remove(self, record_id: str) -> None:
        self._store.pop(record_id, None)

    def stats(self) -> dict[str, Any]:
        return {
            "count": len(self._store),
            "tenants": sorted({r.tenant for r in self._store.values()}),
        }
