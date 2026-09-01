"""C1.6H-3 KnowledgeCard approval and vector promotion tests."""
from __future__ import annotations
from agents.knowledge_card_store import KnowledgeCardStore
from agents.knowledge_card_promoter import KnowledgeCardPromoter


def _setup(tmp_path):
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(
        question="Qwen3 8B VRAM?",
        answer="5-6 GB Q4 ile.",
        source_model="claude-opus-4",
        confidence=85,
    )
    return store, card


class FakeMemory:
    def __init__(self, doc_id="vec_kc_001"):
        self.doc_id = doc_id
        self.calls = []

    def remember(self, user_msg, jarvis_msg, meta=None):
        self.calls.append((user_msg, jarvis_msg, meta or {}))
        return self.doc_id


def test_promote_pending_card_blocked(tmp_path):
    store, card = _setup(tmp_path)
    promoter = KnowledgeCardPromoter(store=store, memory=FakeMemory())
    result = promoter.promote(card["id"])
    assert result["ok"] is False
    assert result["reason"] == "not_approved"


def test_promote_rejected_card_blocked(tmp_path):
    store, card = _setup(tmp_path)
    store.mark_rejected(card["id"])
    promoter = KnowledgeCardPromoter(store=store, memory=FakeMemory())
    result = promoter.promote(card["id"])
    assert result["ok"] is False
    assert result["reason"] == "not_approved"


def test_promote_approved_card_succeeds(tmp_path):
    store, card = _setup(tmp_path)
    store.mark_approved(card["id"])
    promoter = KnowledgeCardPromoter(store=store, memory=FakeMemory("vec_001"))
    result = promoter.promote(card["id"])
    assert result["ok"] is True
    assert result["vector_doc_id"] == "vec_001"
    updated = store.get(card["id"])
    assert updated["storage_status"] == "stored"
    assert updated["vector_doc_id"] == "vec_001"


def test_promote_vector_failure_sets_failed(tmp_path):
    store, card = _setup(tmp_path)
    store.mark_approved(card["id"])
    promoter = KnowledgeCardPromoter(store=store, memory=FakeMemory(doc_id=""))
    result = promoter.promote(card["id"])
    assert result["ok"] is False
    assert result["reason"] == "vector_write_failed"
    updated = store.get(card["id"])
    assert updated["storage_status"] == "failed"
    assert updated["vector_doc_id"] is None


def test_promote_missing_card(tmp_path):
    store = KnowledgeCardStore(data_root=tmp_path)
    promoter = KnowledgeCardPromoter(store=store, memory=FakeMemory())
    result = promoter.promote("nonexistent")
    assert result["ok"] is False
    assert result["reason"] == "card_not_found"


def test_promote_does_not_double_store(tmp_path):
    store, card = _setup(tmp_path)
    store.mark_approved(card["id"])
    memory = FakeMemory("vec_001")
    promoter = KnowledgeCardPromoter(store=store, memory=memory)
    promoter.promote(card["id"])
    result2 = promoter.promote(card["id"])
    assert result2["ok"] is False
    assert result2["reason"] == "already_stored"
    assert len(memory.calls) == 1

def test_promote_card_with_empty_tags(tmp_path):
    """ChromaDB bos liste metadata kabul etmez; tags serialize edilmeli."""
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="Soru?", answer="Cevap.", source_model="m", tags=[])
    store.mark_approved(card["id"])

    memory = FakeMemory("vec_tags_001")
    promoter = KnowledgeCardPromoter(store=store, memory=memory)
    result = promoter.promote(card["id"])

    assert result["ok"] is True
    _, _, meta = memory.calls[0]
    assert isinstance(meta["tags"], str)

