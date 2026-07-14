"""Phase 4 semantic keys: cheap near-duplicate similarity without embeddings."""

from __future__ import annotations

import re
from typing import Protocol

DEFAULT_SHINGLE_SIZE = 2
DEFAULT_THRESHOLD = 0.85


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _shingles(tokens: list[str], k: int = DEFAULT_SHINGLE_SIZE) -> frozenset[str]:
    if len(tokens) <= k:
        return frozenset([" ".join(tokens)])
    return frozenset(" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class SemanticKey(Protocol):
    """Produces a comparable token-shingle set for near-duplicate detection."""

    def shingles(self, text: str) -> frozenset[str]: ...

    def similarity(self, a: str, b: str) -> float: ...


class ShingleSemanticKey:
    """Word-shingle Jaccard similarity. Deterministic and dependency-free."""

    def __init__(self, k: int = DEFAULT_SHINGLE_SIZE) -> None:
        self._k = k

    def shingles(self, text: str) -> frozenset[str]:
        return _shingles(_tokens(text), self._k)

    def similarity(self, a: str, b: str) -> float:
        return jaccard(self.shingles(a), self.shingles(b))
