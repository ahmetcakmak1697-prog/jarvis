"""Y0-3 CostLedger entegrasyonu LocalFirstRouter testleri."""
from __future__ import annotations


class FakeVectorMemory:
    def find_similar(self, *a, **kw):
        return []


class FakeLedgerAllow:
    def check_and_consume(self, call_type="external_call", dry_run=False):
        return {"allowed": True, "reason": "within_limit", "today_count": 1}


class FakeLedgerBlock:
    def check_and_consume(self, call_type="external_call", dry_run=False):
        return {"allowed": False, "reason": "daily_limit_exceeded", "today_count": 50}


def _router(ledger=None, tmp_path=None):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    from pathlib import Path
    import tempfile
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    store = KnowledgeCardStore(data_root=tmp_path)
    return LocalFirstRouter(
        kc_store=store,
        vector_memory=FakeVectorMemory(),
        cost_ledger=ledger,
    )


def test_external_allowed_when_ledger_permits(tmp_path):
    r = _router(ledger=FakeLedgerAllow(), tmp_path=tmp_path)
    result = r.route("tamamen bilinmeyen soru xyz999")
    assert result["decision"] == "ask_external"
    assert result["route"] == "external"


def test_local_answer_survives_external_budget_denial(tmp_path, monkeypatch):
    from b10_execution_support import pipeline

    router = _router(ledger=FakeLedgerBlock(), tmp_path=tmp_path)
    ex, ledger, local, api = pipeline(tmp_path, monkeypatch, cloud=True, router=router)
    ledger.check_and_consume("prior_api")
    result = ex.ask("tamamen bilinmeyen soru xyz999")
    assert result["ok"] is True
    assert result["source"] == "ollama"
    assert result["answer"] == "local answer"
    assert result["primary_failed_executor"] == "api"
    assert api.calls == []
    assert local.calls == ["tamamen bilinmeyen soru xyz999"]
    assert ledger.stats()["today_count"] == 1

def test_local_answer_skips_ledger(tmp_path):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="RTX 3070 kac watt?", answer="220W.", source_model="m", confidence=90)
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_001")

    consumed = []
    class TrackingLedger:
        def check_and_consume(self, call_type="external_call", dry_run=False):
            consumed.append(call_type)
            return {"allowed": True, "reason": "within_limit"}

    r = LocalFirstRouter(kc_store=store, vector_memory=FakeVectorMemory(), cost_ledger=TrackingLedger())
    result = r.route("RTX 3070 kac watt?")
    assert result["route"] == "knowledge_card"
    assert consumed == []
