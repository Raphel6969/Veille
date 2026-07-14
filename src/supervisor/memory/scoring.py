"""Phase 5 memory scoring: deterministic, metadata-driven (no embeddings)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from supervisor.memory.store import MemoryRecord, MemoryTier

RECENCY_HALF_LIFE_HOURS = 24.0


def _recency_score(last_accessed: datetime, now: datetime) -> float:
    age_hours = max(0.0, (now - last_accessed).total_seconds() / 3600.0)
    return float(0.5 ** (age_hours / RECENCY_HALF_LIFE_HOURS))


def _provenance_score(provenance: dict[str, Any]) -> float:
    # Records tied to a specific run/step/agent are more trustworthy.
    if not provenance:
        return 0.3
    score = 0.4
    if provenance.get("run_id"):
        score += 0.2
    if provenance.get("step_id"):
        score += 0.2
    if provenance.get("agent_id"):
        score += 0.2
    return min(1.0, score)


def score(
    record: MemoryRecord,
    now: datetime,
    role_weights: dict[MemoryTier, float] | None = None,
) -> float:
    recency = _recency_score(record.last_accessed, now)
    usage = min(1.0, record.access_count / 5.0)
    conf = max(0.0, min(1.0, record.confidence))
    prov = _provenance_score(record.provenance)
    base = 0.4 * recency + 0.2 * usage + 0.2 * conf + 0.2 * prov
    weight = 1.0
    if role_weights and record.tier in role_weights:
        weight = role_weights[record.tier]
    return round(base * weight, 4)


def default_role_weights() -> dict[MemoryTier, float]:
    # Writers benefit from archived/long-term context; analysts from short-term.
    return {
        MemoryTier.WORKING: 1.0,
        MemoryTier.SHORT: 1.1,
        MemoryTier.LONG: 1.0,
        MemoryTier.ARCHIVE: 0.9,
    }
