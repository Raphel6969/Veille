"""Context compression + diversification reporting.

Builds per-``context.attached`` reports from the event stream. Compression reports
summarize what was compressed and the estimated token delta; diversification reports
measure redundancy among the included slices using shingle Jaccard similarity.

These are additive analytics over existing ``CONTEXT_ATTACHED`` events and the
``ContextManifest`` structure — no new runtime behavior is introduced.
"""

from __future__ import annotations

from pydantic import BaseModel

from supervisor.contracts.events import EventType, RunEventBatch
from supervisor.optimize.keys import ShingleSemanticKey, jaccard

_DIVERSITY_THRESHOLD = 0.85


class CompressionReport(BaseModel):
    step_id: str | None = None
    role: str = ""
    included: int = 0
    excluded: int = 0
    compressed: int = 0
    estimated_tokens: int = 0
    reason: str = ""


class DiversificationReport(BaseModel):
    step_id: str | None = None
    role: str = ""
    included_slices: int = 0
    pairwise_comparisons: int = 0
    redundant_pairs: int = 0
    max_pairwise_similarity: float = 0.0
    coverage_score: float = 0.0
    redundant: bool = False
    detail: str = ""


def _shingles_of(text: str) -> frozenset[str]:
    return ShingleSemanticKey().shingles(text)


def compression_reports(batch: RunEventBatch) -> list[CompressionReport]:
    reports: list[CompressionReport] = []
    for e in batch.events:
        if e.event_type != EventType.CONTEXT_ATTACHED:
            continue
        attrs = e.attributes
        included = attrs.get("included") or []
        excluded = attrs.get("excluded") or []
        compressed = attrs.get("compressed") or []
        reports.append(
            CompressionReport(
                step_id=e.step_id,
                role=str(attrs.get("role", "")),
                included=len(included),
                excluded=len(excluded),
                compressed=len(compressed),
                estimated_tokens=int(attrs.get("estimated_tokens", 0) or 0),
                reason=str(attrs.get("reason", "")),
            )
        )
    return reports


def diversification_reports(batch: RunEventBatch) -> list[DiversificationReport]:
    reports: list[DiversificationReport] = []
    for e in batch.events:
        if e.event_type != EventType.CONTEXT_ATTACHED:
            continue
        attrs = e.attributes
        included = [str(s) for s in (attrs.get("included") or [])]
        n = len(included)
        comparisons = 0
        redundant = 0
        max_sim = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                sim = jaccard(_shingles_of(included[i]), _shingles_of(included[j]))
                comparisons += 1
                if sim > max_sim:
                    max_sim = sim
                if sim >= _DIVERSITY_THRESHOLD:
                    redundant += 1
        coverage = round(1.0 - (redundant / comparisons), 3) if comparisons else 1.0
        reports.append(
            DiversificationReport(
                step_id=e.step_id,
                role=str(attrs.get("role", "")),
                included_slices=n,
                pairwise_comparisons=comparisons,
                redundant_pairs=redundant,
                max_pairwise_similarity=round(max_sim, 3),
                coverage_score=coverage,
                redundant=redundant > 0,
                detail=(
                    f"{redundant} redundant pair(s) among {n} slices"
                    if redundant
                    else "included slices are sufficiently diverse"
                ),
            )
        )
    return reports
