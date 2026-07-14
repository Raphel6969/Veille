"""Phase 4 optimization package: semantic dedup + adaptive caching."""

from supervisor.optimize.cache import (
    CacheBackend,
    FileCacheBackend,
    InMemoryCache,
    make_backend,
)
from supervisor.optimize.dedup import DuplicateDetector, DuplicateMatch
from supervisor.optimize.keys import (
    DEFAULT_SHINGLE_SIZE,
    DEFAULT_THRESHOLD,
    SemanticKey,
    ShingleSemanticKey,
    jaccard,
)

__all__ = [
    "CacheBackend",
    "InMemoryCache",
    "FileCacheBackend",
    "make_backend",
    "DuplicateDetector",
    "DuplicateMatch",
    "SemanticKey",
    "ShingleSemanticKey",
    "jaccard",
    "DEFAULT_SHINGLE_SIZE",
    "DEFAULT_THRESHOLD",
]
