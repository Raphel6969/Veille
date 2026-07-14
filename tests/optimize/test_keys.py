from supervisor.optimize.keys import ShingleSemanticKey, jaccard


def test_identical_texts_have_similarity_one() -> None:
    key = ShingleSemanticKey()
    assert key.similarity("the quick brown fox", "the quick brown fox") == 1.0


def test_disjoint_texts_have_similarity_zero() -> None:
    key = ShingleSemanticKey()
    assert key.similarity("alpha beta", "gamma delta") == 0.0


def test_similar_texts_have_partial_similarity() -> None:
    key = ShingleSemanticKey()
    sim = key.similarity("the quick brown fox jumps", "the quick brown fox leaps")
    assert 0.0 < sim < 1.0


def test_jaccard_helper() -> None:
    assert jaccard(frozenset({"a", "b"}), frozenset({"a", "b"})) == 1.0
    assert jaccard(frozenset({"a"}), frozenset({"b"})) == 0.0
