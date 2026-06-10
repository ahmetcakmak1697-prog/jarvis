"""Y0 LocalFirstRouter tests."""
from __future__ import annotations


def test_router_returns_required_fields():
    from agents.local_first_router import LocalFirstRouter
    r = LocalFirstRouter()
    result = r.route("RTX 3070 kac watt?")
    assert "decision" in result
    assert "route" in result
    assert "confidence" in result
    assert "reason" in result
    assert "signals" in result


def test_decision_values_valid():
    from agents.local_first_router import LocalFirstRouter
    r = LocalFirstRouter()
    result = r.route("herhangi bir soru")
    assert result["decision"] in ("answer_local", "ask_external", "clarify", "no_answer")


def test_route_values_valid():
    from agents.local_first_router import LocalFirstRouter
    r = LocalFirstRouter()
    result = r.route("herhangi bir soru")
    assert result["route"] in ("knowledge_card", "memory", "external", "clarify")


def test_known_card_routes_local(tmp_path):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore

    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(
        question="RTX 3070 kac watt?",
        answer="220W TDP.",
        source_model="claude-opus-4",
        confidence=90,
    )
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_001")

    r = LocalFirstRouter(kc_store=store)
    result = r.route("RTX 3070 kac watt?")
    assert result["decision"] == "answer_local"
    assert result["route"] == "knowledge_card"


def test_unknown_question_routes_external():
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        store = KnowledgeCardStore(data_root=Path(td))
        r = LocalFirstRouter(kc_store=store)
        result = r.route("tamamen bilinmeyen ve cok ozel bir soru xyz123")
        assert result["decision"] == "ask_external"
        assert result["route"] == "external"


def test_confidence_is_int_or_float():
    from agents.local_first_router import LocalFirstRouter
    r = LocalFirstRouter()
    result = r.route("test sorusu")
    assert isinstance(result["confidence"], (int, float))
    assert 0 <= result["confidence"] <= 100


def test_no_side_effects(tmp_path):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    import os
    store = KnowledgeCardStore(data_root=tmp_path)
    before = set(os.listdir(tmp_path))
    r = LocalFirstRouter(kc_store=store)
    r.route("test")
    after = set(os.listdir(tmp_path))
    assert before == after
