"""Phase 4 near-duplicate detector (exact + semantic), in-run index."""

from __future__ import annotations

from dataclasses import dataclass

from supervisor.optimize.keys import (
    DEFAULT_THRESHOLD,
    SemanticKey,
    ShingleSemanticKey,
)


@dataclass
class DuplicateMatch:
    """A detected near-duplicate of a previously seen call."""

    match_type: str  # "exact" | "semantic"
    similarity: float  # 0..1
    cache_key: str  # exact key of the prior call to serve/lookup


@dataclass
class _Entry:
    tool_name: str
    exact_key: str
    text: str


class DuplicateDetector:
    """Indexes seen (tool, input) calls and reports near-duplicates.

    Exact matches reuse the identical ``exact_key``. Semantic matches reuse the
    prior call whose input is within ``threshold`` Jaccard similarity. Both
    return the prior call's ``exact_key`` so the caller can serve from cache.
    """

    def __init__(
        self,
        key: SemanticKey | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self._key = key or ShingleSemanticKey()
        self._threshold = threshold
        self._entries: list[_Entry] = []

    def check(
        self, tool_name: str, normalized_input: str, exact_key: str
    ) -> DuplicateMatch | None:
        for entry in self._entries:
            if entry.tool_name == tool_name and entry.exact_key == exact_key:
                self._entries.append(_Entry(tool_name, exact_key, normalized_input))
                return DuplicateMatch("exact", 1.0, entry.exact_key)
        best: _Entry | None = None
        best_sim = 0.0
        for entry in self._entries:
            if entry.tool_name != tool_name:
                continue
            sim = self._key.similarity(entry.text, normalized_input)
            if sim >= self._threshold and sim > best_sim:
                best_sim = sim
                best = entry
        self._entries.append(_Entry(tool_name, exact_key, normalized_input))
        if best is not None:
            return DuplicateMatch("semantic", round(best_sim, 4), best.exact_key)
        return None
