"""Y1 ModelCascade entegrasyonu LocalFirstRouter testleri."""
from __future__ import annotations


class FakeVectorMemory:
    def find_similar(self, *a, **kw):
        return []


class FakeLedgerAllow:
    def check_and_consume(self, *a, **kw):
        return {"allowed": True, "reason": "within_limit"}


def _router(tmp_path):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    return LocalFirstRouter(
        kc_store=store,
        vector_memory=FakeVectorMemory(),
        cost_ledger=FakeLedgerAllow(),
    )


def test_external_result_has_cascade_level(tmp_path):
    r = _router(tmp_path)
    result = r.route("bilinmeyen soru xyz999")
    assert result["decision"] == "ask_external"
    assert "cascade" in result
    assert "level" in result["cascade"]
    assert "model" in result["cascade"]
    assert "cost_tier" in result["cascade"]


def test_deep_question_gets_L3(tmp_path):
    r = _router(tmp_path)
    result = r.route("derinlemesine analiz et ve detayli rapor hazirla")
    assert result["decision"] == "ask_external"
    assert result["cascade"]["level"] == "L3"


def test_simple_question_gets_L1_or_L2(tmp_path):
    r = _router(tmp_path)
    result = r.route("merhaba")
    if result["decision"] == "ask_external":
        assert result["cascade"]["level"] in ("L1", "L2")


def test_local_answer_has_no_cascade(tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.local_first_router import LocalFirstRouter
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="RTX 3070 kac watt?", answer="220W.", source_model="m", confidence=90)
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_001")
    r = LocalFirstRouter(kc_store=store, vector_memory=FakeVectorMemory(), cost_ledger=FakeLedgerAllow())
    result = r.route("RTX 3070 kac watt?")
    assert result["decision"] == "answer_local"
    assert result.get("cascade") is None
