"""Y0-4 Escalation reason + crystallize candidate testleri."""
from __future__ import annotations


class FakeVectorMemory:
    def find_similar(self, *a, **kw):
        return []


class FakeLedgerAllow:
    def check_and_consume(self, *a, **kw):
        return {"allowed": True, "reason": "within_limit"}


class FakeLedgerBlock:
    def check_and_consume(self, *a, **kw):
        return {"allowed": False, "reason": "daily_limit_exceeded"}


def _router(ledger=None, kc_store=None, tmp_path=None):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    from pathlib import Path
    import tempfile
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    store = kc_store or KnowledgeCardStore(data_root=tmp_path)
    return LocalFirstRouter(
        kc_store=store,
        vector_memory=FakeVectorMemory(),
        cost_ledger=ledger or FakeLedgerAllow(),
    )


def test_external_has_escalation_reason(tmp_path):
    r = _router(tmp_path=tmp_path)
    result = r.route("bilinmeyen soru xyz999")
    assert result["decision"] == "ask_external"
    assert "escalation_reason" in result
    assert isinstance(result["escalation_reason"], str)
    assert len(result["escalation_reason"]) > 0


def test_external_has_checked_sources(tmp_path):
    r = _router(tmp_path=tmp_path)
    result = r.route("bilinmeyen soru xyz999")
    assert "checked_sources" in result
    assert isinstance(result["checked_sources"], list)
    assert "knowledge_card" in result["checked_sources"]
    assert "memory" in result["checked_sources"]


def test_external_has_crystallize_candidate(tmp_path):
    r = _router(tmp_path=tmp_path)
    result = r.route("bilinmeyen soru xyz999")
    assert result["decision"] == "ask_external"
    cand = result.get("crystallize_candidate")
    assert cand is not None
    assert cand["question"] == "bilinmeyen soru xyz999"
    assert "checked_sources" in cand
    assert cand["status"] == "pending_crystallization"


def test_blocked_has_no_crystallize_candidate(tmp_path):
    r = _router(ledger=FakeLedgerBlock(), tmp_path=tmp_path)
    result = r.route("bilinmeyen soru xyz999")
    assert result["decision"] == "external_blocked"
    assert result.get("crystallize_candidate") is None


def test_local_answer_has_no_crystallize_candidate(tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="RTX 3070 kac watt?", answer="220W.", source_model="m", confidence=90)
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_001")
    r = _router(kc_store=store, tmp_path=tmp_path)
    result = r.route("RTX 3070 kac watt?")
    assert result["decision"] == "answer_local"
    assert result.get("crystallize_candidate") is None
