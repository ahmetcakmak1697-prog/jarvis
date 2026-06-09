"""C1.6H-2 AnswerCrystallizer tests."""
from __future__ import annotations


def _crystallizer(tmp_path, **kwargs):
    from agents.answer_crystallizer import AnswerCrystallizer
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    return AnswerCrystallizer(store=store, **kwargs)


def test_crystallize_returns_card(tmp_path):
    cr = _crystallizer(tmp_path)
    card = cr.crystallize(
        question="Qwen3 8B kac GB VRAM harcar?",
        answer="Q4 ile yaklasik 5-6 GB.",
        source_model="claude-opus-4",
    )
    assert card["review_status"] == "pending"
    assert card["storage_status"] == "draft"
    assert card["vector_doc_id"] is None
    assert card["source_type"] == "answer_crystallization"


def test_crystallize_persists_to_store(tmp_path):
    cr = _crystallizer(tmp_path)
    card = cr.crystallize(
        question="Test sorusu?",
        answer="Test cevabi.",
        source_model="gpt-5",
    )
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    found = store.get(card["id"])
    assert found is not None
    assert found["id"] == card["id"]


def test_crystallize_no_vector_write(tmp_path):
    """crystallize() hicbir sekilde VectorMemory.remember() cagirmamali."""
    calls = []

    class FakeMemory:
        def remember(self, *a, **kw):
            calls.append((a, kw))
            return "vec_x"

    cr = _crystallizer(tmp_path)
    cr.crystallize(
        question="Soru?",
        answer="Cevap.",
        source_model="test-model",
    )
    assert calls == []


def test_crystallize_with_domain_and_tags(tmp_path):
    cr = _crystallizer(tmp_path)
    card = cr.crystallize(
        question="RTX 3070 kac watt?",
        answer="TDP 220W.",
        source_model="claude-opus-4",
        domain="hardware",
        tags=["gpu", "power"],
        confidence=90,
    )
    assert card["domain"] == "hardware"
    assert "gpu" in card["tags"]
    assert card["confidence"] == 90


def test_crystallize_rejects_empty_question(tmp_path):
    import pytest
    cr = _crystallizer(tmp_path)
    with pytest.raises(ValueError):
        cr.crystallize(question="", answer="Cevap.", source_model="m")


def test_crystallize_rejects_empty_answer(tmp_path):
    import pytest
    cr = _crystallizer(tmp_path)
    with pytest.raises(ValueError):
        cr.crystallize(question="Soru?", answer="", source_model="m")


def test_crystallize_schema_version(tmp_path):
    cr = _crystallizer(tmp_path)
    card = cr.crystallize(
        question="Soru?", answer="Cevap.", source_model="m"
    )
    assert card["schema_version"] == "c1.6h"
