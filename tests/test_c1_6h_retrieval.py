"""C1.6H-5 KnowledgeCard retrieval-first lookup tests."""
from __future__ import annotations
from agents.knowledge_card_store import KnowledgeCardStore
from agents.knowledge_card_retriever import KnowledgeCardRetriever


def _store_with_card(tmp_path, question, answer, model="claude-opus-4",
                     confidence=85, review_status="approved", storage_status="stored"):
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question=question, answer=answer,
                     source_model=model, confidence=confidence)
    if review_status == "approved":
        store.mark_approved(card["id"])
    if storage_status == "stored":
        store.mark_stored(card["id"], vector_doc_id="vec_001")
    return store, card


def test_retriever_finds_exact_match(tmp_path):
    store, card = _store_with_card(tmp_path, "RTX 3070 kac watt?", "220W TDP.")
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("RTX 3070 kac watt?")
    assert result["found"] is True
    assert result["card"]["id"] == card["id"]
    assert result["answer"] == "220W TDP."


def test_retriever_returns_not_found_for_unknown(tmp_path):
    store = KnowledgeCardStore(data_root=tmp_path)
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("tamamen bilinmeyen soru xyzxyz")
    assert result["found"] is False
    assert result["answer"] is None


def test_retriever_skips_pending_cards(tmp_path):
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="Soru?", answer="Cevap.", source_model="m")
    # pending/draft - retrieve edilmemeli
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("Soru?")
    assert result["found"] is False


def test_retriever_skips_low_confidence(tmp_path):
    store, card = _store_with_card(
        tmp_path, "Dusuk guven sorusu?", "Belirsiz cevap.",
        confidence=30
    )
    r = KnowledgeCardRetriever(store=store, min_confidence=50)
    result = r.lookup("Dusuk guven sorusu?")
    assert result["found"] is False


def test_retriever_finds_partial_match(tmp_path):
    store, card = _store_with_card(
        tmp_path, "Qwen3 8B modeli kac GB VRAM harcar?", "5-6 GB Q4 ile."
    )
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("Qwen3 8B VRAM")
    assert result["found"] is True


def test_retriever_returns_source_model(tmp_path):
    store, card = _store_with_card(
        tmp_path, "Test sorusu?", "Test cevabi.", model="gpt-5"
    )
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("Test sorusu?")
    assert result["found"] is True
    assert result["source_model"] == "gpt-5"


def test_retriever_no_side_effects(tmp_path):
    store, card = _store_with_card(tmp_path, "Soru?", "Cevap.")
    r = KnowledgeCardRetriever(store=store)
    r.lookup("Soru?")
    updated = store.get(card["id"])
    assert updated["storage_status"] == "stored"
    assert updated["review_status"] == "approved"
