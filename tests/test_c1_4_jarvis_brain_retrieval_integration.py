"""C1.4 JarvisBrain retrieval policy integration smoke tests."""

from __future__ import annotations

from agents.memory_retrieval_policy import MemoryRetrievalPolicy


def test_memory_retrieval_policy_allows_safe_hit():
    policy = MemoryRetrievalPolicy(max_items=3, min_similarity=0.70)

    safe = policy.filter_hits([
        {
            "id": "safe_memory",
            "similarity": 0.90,
            "user_msg": "Jarvis C1 hafıza politikası",
            "jarvis_msg": "C1 retrieval policy aktif.",
            "metadata": {
                "memory_action": "keep_long_term",
                "memory_type": "semantic",
                "storage_target": "vector",
                "sensitivity": "normal",
                "memory_importance": 9,
            },
        }
    ])

    assert len(safe) == 1
    assert safe[0]["id"] == "safe_memory"
    assert safe[0]["retrieval_meta"]["reason"] == "allowed"


def test_memory_retrieval_policy_blocks_unsafe_hit():
    policy = MemoryRetrievalPolicy(max_items=3, min_similarity=0.70)

    safe = policy.filter_hits([
        {
            "id": "unsafe_memory",
            "similarity": 0.95,
            "user_msg": "telefon numaram",
            "jarvis_msg": "hassas bilgi",
            "metadata": {
                "memory_action": "sensitive_review",
                "memory_type": "sensitive_review",
                "storage_target": "review_queue",
                "sensitivity": "sensitive",
                "requires_review": True,
            },
        }
    ])

    assert safe == []


def test_jarvis_brain_class_imports():
    from jarvis_brain import JarvisBrain

    assert JarvisBrain is not None
