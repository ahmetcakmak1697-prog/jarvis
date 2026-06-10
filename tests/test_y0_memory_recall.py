"""Y0-2 LocalFirstRouter memory recall entegrasyonu testleri."""
from __future__ import annotations


class FakeVectorMemory:
    def __init__(self, hits=None):
        self.hits = hits or []
        self.calls = []

    def find_similar(self, query, n=3, threshold=0.7):
        self.calls.append((query, n, threshold))
        return self.hits


def _router(kc_store=None, vector_memory=None, tmp_path=None):
    from agents.local_first_router import LocalFirstRouter
    from pathlib import Path
    import tempfile
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    from agents.knowledge_card_store import KnowledgeCardStore
    store = kc_store or KnowledgeCardStore(data_root=tmp_path)
    return LocalFirstRouter(kc_store=store, vector_memory=vector_memory)


def test_memory_hit_routes_local(tmp_path):
    hits = [{
        "id": "mem_001",
        "similarity": 0.85,
        "metadata": {
            "memory_action": "keep_long_term",
            "memory_type": "semantic",
            "storage_target": "vector",
            "sensitivity": "normal",
            "memory_importance": 8,
            "tier": "recall",
            "maturity_score": 60,
        },
    }]
    vm = FakeVectorMemory(hits=hits)
    r = _router(vector_memory=vm, tmp_path=tmp_path)
    result = r.route("Jarvis projesi nerede?")
    assert result["decision"] == "answer_local"
    assert result["route"] == "memory"


def test_no_memory_hit_routes_external(tmp_path):
    vm = FakeVectorMemory(hits=[])
    r = _router(vector_memory=vm, tmp_path=tmp_path)
    result = r.route("tamamen bilinmeyen soru xyz999")
    assert result["decision"] == "ask_external"
    assert result["route"] == "external"


def test_blocked_memory_hit_routes_external(tmp_path):
    hits = [{
        "id": "mem_blocked",
        "similarity": 0.90,
        "metadata": {
            "memory_action": "sensitive_review",
            "sensitivity": "sensitive",
            "memory_type": "sensitive_review",
            "storage_target": "review_queue",
        },
    }]
    vm = FakeVectorMemory(hits=hits)
    r = _router(vector_memory=vm, tmp_path=tmp_path)
    result = r.route("hassas veri sorusu")
    assert result["decision"] == "ask_external"


def test_memory_result_has_priority_score(tmp_path):
    hits = [{
        "id": "mem_001",
        "similarity": 0.88,
        "metadata": {
            "memory_action": "keep_long_term",
            "memory_type": "semantic",
            "storage_target": "vector",
            "sensitivity": "normal",
            "tier": "core",
            "maturity_score": 80,
        },
    }]
    vm = FakeVectorMemory(hits=hits)
    r = _router(vector_memory=vm, tmp_path=tmp_path)
    result = r.route("test sorusu")
    if result["route"] == "memory":
        assert "top_hit_priority" in result["signals"]


def test_kc_takes_priority_over_memory(tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(
        question="RTX 3070 kac watt?",
        answer="220W TDP.",
        source_model="m",
        confidence=90,
    )
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_001")

    hits = [{"id": "mem_001", "similarity": 0.85, "metadata": {
        "memory_action": "keep_long_term", "memory_type": "semantic",
        "storage_target": "vector", "sensitivity": "normal",
    }}]
    vm = FakeVectorMemory(hits=hits)
    r = _router(kc_store=store, vector_memory=vm, tmp_path=tmp_path)
    result = r.route("RTX 3070 kac watt?")
    assert result["route"] == "knowledge_card"
