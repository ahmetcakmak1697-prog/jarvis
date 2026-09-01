"""C1.7 RetrievalPriorityRanker tests."""
from __future__ import annotations


def _hit(id, similarity=0.80, tier="recall", maturity_score=50, importance=5):
    return {
        "id": id,
        "similarity": similarity,
        "metadata": {
            "memory_action": "keep_long_term",
            "memory_type": "semantic",
            "storage_target": "vector",
            "sensitivity": "normal",
            "memory_importance": importance,
            "tier": tier,
            "maturity_score": maturity_score,
        },
    }


def test_ranker_returns_list():
    from agents.retrieval_priority import RetrievalPriorityRanker
    r = RetrievalPriorityRanker()
    result = r.rank([_hit("m1"), _hit("m2")])
    assert isinstance(result, list)
    assert len(result) == 2


def test_core_tier_ranked_above_episodic():
    from agents.retrieval_priority import RetrievalPriorityRanker
    r = RetrievalPriorityRanker()
    hits = [
        _hit("episodic", tier="episodic", similarity=0.85),
        _hit("core", tier="core", similarity=0.85),
    ]
    ranked = r.rank(hits)
    assert ranked[0]["id"] == "core"


def test_high_maturity_ranked_above_low():
    from agents.retrieval_priority import RetrievalPriorityRanker
    r = RetrievalPriorityRanker()
    hits = [
        _hit("low", maturity_score=10, similarity=0.82),
        _hit("high", maturity_score=90, similarity=0.82),
    ]
    ranked = r.rank(hits)
    assert ranked[0]["id"] == "high"


def test_priority_score_in_output():
    from agents.retrieval_priority import RetrievalPriorityRanker
    r = RetrievalPriorityRanker()
    ranked = r.rank([_hit("m1")])
    assert "priority_score" in ranked[0]
    assert isinstance(ranked[0]["priority_score"], float)


def test_empty_input_returns_empty():
    from agents.retrieval_priority import RetrievalPriorityRanker
    r = RetrievalPriorityRanker()
    assert r.rank([]) == []


def test_max_items_respected():
    from agents.retrieval_priority import RetrievalPriorityRanker
    r = RetrievalPriorityRanker(max_items=2)
    hits = [_hit(f"m{i}") for i in range(5)]
    assert len(r.rank(hits)) == 2


def test_no_side_effects():
    from agents.retrieval_priority import RetrievalPriorityRanker
    import copy
    r = RetrievalPriorityRanker()
    original = [_hit("m1"), _hit("m2")]
    before = copy.deepcopy(original)
    r.rank(original)
    assert original == before
