"""Phase 5 memory governor: per-step/role retrieval governance with reasons."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from supervisor.memory.scoring import default_role_weights, score
from supervisor.memory.store import MemoryBackend, MemoryRecord, MemoryTier


class MemoryManifest(BaseModel):
    """Per-step decision of which memories a role should see, and why."""

    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    stale: list[str] = Field(default_factory=list)
    drift: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    reason: str = ""


class MemoryGovernor:
    """Decides memory inclusion per step/role; flags stale/drift; audits expiry."""

    def __init__(
        self,
        stale_after: timedelta = timedelta(days=7),
        min_confidence: float = 0.3,
        min_score: float = 0.2,
        drift_threshold: float = 0.0,
    ) -> None:
        self.stale_after = stale_after
        self.min_confidence = min_confidence
        self.min_score = min_score
        self.drift_threshold = drift_threshold

    def retrieve(
        self,
        backend: MemoryBackend,
        query: str,
        role: str,
        *,
        tenant: str = "default",
        limit: int = 5,
        role_weights: dict[MemoryTier, float] | None = None,
        now: datetime | None = None,
    ) -> tuple[list[MemoryRecord], MemoryManifest]:
        now = now or datetime.now(UTC)
        weights = role_weights or default_role_weights()
        candidates = backend.retrieve(query, role, tenant)
        included: list[str] = []
        excluded: list[str] = []
        stale: list[str] = []
        drift: list[str] = []
        scores: dict[str, float] = {}

        ranked: list[tuple[float, MemoryRecord]] = []
        for rec in candidates:
            s = score(rec, now, weights)
            scores[rec.id] = s
            age = now - rec.last_accessed
            is_stale = age > self.stale_after or rec.confidence < self.min_confidence
            is_drift = bool(rec.baseline_hash) and rec.baseline_hash != rec.content_hash_now()
            if is_stale:
                stale.append(rec.id)
            if is_drift:
                drift.append(rec.id)
            if is_stale or is_drift or s < self.min_score:
                excluded.append(rec.id)
                continue
            ranked.append((s, rec))

        ranked.sort(key=lambda x: x[0], reverse=True)
        chosen = ranked[:limit]
        for _, rec in chosen:
            included.append(rec.id)
            backend.record_access(rec.id)

        reason = (
            f"Role '{role}' retrieved {len(included)} of {len(candidates)} candidate "
            f"memories (stale={len(stale)}, drift={len(drift)})."
        )
        manifest = MemoryManifest(
            included=included,
            excluded=excluded,
            stale=stale,
            drift=drift,
            scores=scores,
            reason=reason,
        )
        return [rec for _, rec in chosen], manifest

    def expire_due(self, backend: MemoryBackend, now: datetime | None = None) -> list[MemoryRecord]:
        # Surfaces candidates for audited removal; never deletes.
        return backend.due_for_expiry(now)
