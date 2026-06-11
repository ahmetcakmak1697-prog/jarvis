"""KnowledgeCardRetriever precision regression tests."""
from __future__ import annotations


def _store_with_qwen(tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(
        question="Qwen3 8B modeli RTX 3070 8GB da nasil calistirilir?",
        answer="ollama pull qwen3:8b komutuyla indirilir.",
        source_model="test",
        confidence=90,
    )
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_test")
    return store


def test_python_question_does_not_match_qwen_card(tmp_path):
    from agents.knowledge_card_retriever import KnowledgeCardRetriever
    store = _store_with_qwen(tmp_path)
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("Python listede tekrar eden elemanlari nasil buluruz?")
    assert result["found"] is False


def test_qwen_question_matches_qwen_card(tmp_path):
    from agents.knowledge_card_retriever import KnowledgeCardRetriever
    store = _store_with_qwen(tmp_path)
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("Qwen3 8B modeli RTX 3070 8GB da nasil calistirilir?")
    assert result["found"] is True
    assert "ollama pull" in result["answer"]
    assert 0.0 <= result["score"] <= 1.0


def test_digit_difference_blocks_wrong_hardware(tmp_path):
    from agents.knowledge_card_retriever import KnowledgeCardRetriever
    store = _store_with_qwen(tmp_path)
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("Qwen3 8B modeli RTX 4090 24GB da nasil calistirilir?")
    assert result["found"] is False


def test_negation_mismatch_blocks_match(tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.knowledge_card_retriever import KnowledgeCardRetriever
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="RTX 3070 ekran karti iyi mi?",
                     answer="Evet, iyi.", source_model="test", confidence=90)
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_001")
    r = KnowledgeCardRetriever(store=store)
    result = r.lookup("RTX 3070 ekran karti iyi degil mi?")
    assert result["found"] is False


def test_router_returns_answer_field(tmp_path):
    from agents.local_first_router import LocalFirstRouter
    store = _store_with_qwen(tmp_path)
    router = LocalFirstRouter(kc_store=store)
    result = router.route("Qwen3 8B modeli RTX 3070 8GB da nasil calistirilir?")
    assert result["decision"] == "answer_local"
    assert result["route"] == "knowledge_card"
    assert "answer" in result
    assert result["answer"] is not None
    assert "ollama pull" in result["answer"]
