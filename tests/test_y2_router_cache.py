"""Y2-1 QueryCache entegrasyonu LocalFirstRouter testleri."""
from __future__ import annotations


class FakeVectorMemory:
    def find_similar(self, *a, **kw):
        return []


class FakeLedgerAllow:
    def check_and_consume(self, *a, **kw):
        return {"allowed": True, "reason": "within_limit"}


def _router(tmp_path, cache=None):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    return LocalFirstRouter(
        kc_store=store,
        vector_memory=FakeVectorMemory(),
        cost_ledger=FakeLedgerAllow(),
        query_cache=cache,
    )


def test_cache_hit_returns_answer_local(tmp_path):
    from agents.query_cache import QueryCache
    cache = QueryCache(data_root=tmp_path)
    cache.put("RTX 3070 kac watt?", "220W TDP.", source_route="cache")

    r = _router(tmp_path, cache=cache)
    result = r.route("RTX 3070 kac watt?")
    assert result["decision"] == "answer_local"
    assert result["route"] == "cache"
    assert result["answer"] == "220W TDP."


def test_cache_miss_continues_normal_flow(tmp_path):
    from agents.query_cache import QueryCache
    cache = QueryCache(data_root=tmp_path)

    r = _router(tmp_path, cache=cache)
    result = r.route("tamamen bilinmeyen soru xyz999")
    assert result["decision"] in ("ask_external", "answer_local")
    assert result["route"] != "cache"


def test_cache_hit_has_no_cascade(tmp_path):
    from agents.query_cache import QueryCache
    cache = QueryCache(data_root=tmp_path)
    cache.put("Soru?", "Cevap.", source_route="cache")

    r = _router(tmp_path, cache=cache)
    result = r.route("Soru?")
    assert result["route"] == "cache"
    assert result.get("cascade") is None


def test_no_cache_still_works(tmp_path):
    r = _router(tmp_path, cache=None)
    result = r.route("test sorusu")
    assert "decision" in result
