"""C1.4 Memory retrieval policy tests."""

from __future__ import annotations

from agents.memory_retrieval_policy import MemoryRetrievalPolicy


def _hit(candidate_id: str, similarity: float, metadata: dict) -> dict:
    return {
        "id": candidate_id,
        "similarity": similarity,
        "metadata": metadata,
    }


def test_allows_safe_semantic_vector_memory():
    policy = MemoryRetrievalPolicy(max_items=5, min_similarity=0.70)

    safe = policy.filter_hits([
        _hit("m1", 0.84, {
            "memory_action": "keep_long_term",
            "memory_type": "semantic",
            "storage_target": "vector",
            "sensitivity": "normal",
            "memory_tags": "explicit_save,project",
            "memory_importance": 9,
        })
    ])

    assert len(safe) == 1
    assert safe[0]["id"] == "m1"
    assert safe[0]["retrieval_meta"]["allowed"] is True
    assert safe[0]["retrieval_meta"]["reason"] == "allowed"


def test_blocks_sensitive_review_memory():
    policy = MemoryRetrievalPolicy()

    safe = policy.filter_hits([
        _hit("sensitive", 0.95, {
            "memory_action": "sensitive_review",
            "memory_type": "sensitive_review",
            "storage_target": "review_queue",
            "sensitivity": "sensitive",
            "requires_review": True,
        })
    ])

    assert safe == []


def test_blocks_expired_pending_rejected_statuses():
    policy = MemoryRetrievalPolicy()
    hits = [
        _hit("expired", 0.92, {"status": "expired", "memory_action": "keep_long_term"}),
        _hit("pending", 0.92, {"status": "pending_review", "memory_action": "keep_long_term"}),
        _hit("rejected", 0.92, {"status": "rejected", "memory_action": "keep_long_term"}),
        _hit("deferred", 0.92, {"status": "deferred", "memory_action": "keep_long_term"}),
    ]

    assert policy.filter_hits(hits) == []


def test_blocks_low_similarity_hits():
    policy = MemoryRetrievalPolicy(min_similarity=0.70)

    safe = policy.filter_hits([
        _hit("low", 0.40, {
            "memory_action": "keep_long_term",
            "memory_type": "semantic",
            "storage_target": "vector",
            "sensitivity": "normal",
        })
    ])

    assert safe == []


def test_limits_max_items_and_sorts_by_score():
    policy = MemoryRetrievalPolicy(max_items=2, min_similarity=0.70)

    hits = [
        _hit("m1", 0.80, {"memory_action": "keep_long_term", "memory_type": "semantic"}),
        _hit("m2", 0.90, {"memory_action": "keep_long_term", "memory_type": "semantic"}),
        _hit("m3", 0.85, {"memory_action": "keep_long_term", "memory_type": "semantic"}),
    ]

    safe = policy.filter_hits(hits)

    assert len(safe) == 2
    assert safe[0]["id"] == "m2"
    assert safe[1]["id"] == "m3"


def test_blocks_vector_not_allowed_when_action_present():
    policy = MemoryRetrievalPolicy()

    safe = policy.filter_hits([
        _hit("blocked", 0.90, {
            "memory_action": "keep_long_term",
            "allow_vector": False,
            "memory_type": "semantic",
        })
    ])

    assert safe == []
