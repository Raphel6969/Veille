from supervisor.optimize.dedup import DuplicateDetector

EXACT_A = '{"query": "competitor landscape"}'
EXACT_B = '{"query": "competitor landscape"}'
SIMILAR = '{"query": "competitor landscape overview"}'
DIFFERENT = '{"query": "stock prices"}'


def test_exact_duplicate_detected() -> None:
    det = DuplicateDetector()
    det.check("search", EXACT_A, "k1")
    match = det.check("search", EXACT_B, "k1")
    assert match is not None
    assert match.match_type == "exact"
    assert match.similarity == 1.0


def test_semantic_duplicate_detected_within_threshold() -> None:
    det = DuplicateDetector(threshold=0.5)
    det.check("search", EXACT_A, "k1")
    match = det.check("search", SIMILAR, "k2")
    assert match is not None
    assert match.match_type == "semantic"
    assert 0.0 < match.similarity < 1.0


def test_no_match_below_threshold() -> None:
    det = DuplicateDetector()
    det.check("search", EXACT_A, "k1")
    match = det.check("search", SIMILAR, "k2")
    assert match is None


def test_different_tool_not_matched() -> None:
    det = DuplicateDetector()
    det.check("search", EXACT_A, "k1")
    match = det.check("fetch", EXACT_A, "k2")
    assert match is None


def test_cache_key_points_to_prior_call() -> None:
    det = DuplicateDetector(threshold=0.5)
    det.check("search", EXACT_A, "k1")
    match = det.check("search", SIMILAR, "k2")
    assert match is not None
    assert match.cache_key == "k1"
