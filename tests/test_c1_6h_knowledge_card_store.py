"""C1.6H-1 KnowledgeCardStore invariant tests."""
from __future__ import annotations
import json


# --- helpers ---

def _store(tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    return KnowledgeCardStore(data_root=tmp_path)


def _valid_card(**overrides):
    base = {
        "question": "Qwen3 8B kac GB VRAM harcar?",
        "answer": "Q4 ile yaklasik 5-6 GB VRAM.",
        "source_model": "claude-opus-4",
        "domain": "hardware",
        "tags": ["vram", "qwen3"],
        "confidence": 85,
    }
    base.update(overrides)
    return base


# --- invariant 1-3: new card pending/draft/null ---

def test_new_card_review_status_is_pending(tmp_path):
    card = _store(tmp_path).add(_valid_card())
    assert card["review_status"] == "pending"


def test_new_card_storage_status_is_draft(tmp_path):
    card = _store(tmp_path).add(_valid_card())
    assert card["storage_status"] == "draft"


def test_new_card_vector_doc_id_is_none(tmp_path):
    card = _store(tmp_path).add(_valid_card())
    assert card["vector_doc_id"] is None


# --- invariant 4-6: validation ---

def test_rejects_empty_question(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="question"):
        _store(tmp_path).add(_valid_card(question=""))


def test_rejects_empty_answer(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="answer"):
        _store(tmp_path).add(_valid_card(answer=""))


def test_rejects_empty_source_model(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="source_model"):
        _store(tmp_path).add(_valid_card(source_model=""))


# --- invariant 7: confidence range ---

def test_rejects_confidence_out_of_range(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="confidence"):
        _store(tmp_path).add(_valid_card(confidence=150))
    with pytest.raises(ValueError, match="confidence"):
        _store(tmp_path).add(_valid_card(confidence=-1))


# --- invariant 8-9: stored <-> vector_doc_id sync ---

def test_stored_card_requires_vector_doc_id(tmp_path):
    import pytest
    store = _store(tmp_path)
    card = store.add(_valid_card())
    with pytest.raises(ValueError, match="vector_doc_id"):
        store.mark_stored(card["id"], vector_doc_id="")


def test_vector_doc_id_implies_stored_status(tmp_path):
    store = _store(tmp_path)
    card = store.add(_valid_card())
    store.mark_approved(card["id"])
    updated = store.mark_stored(card["id"], vector_doc_id="vec_001")
    assert updated["storage_status"] == "stored"
    assert updated["vector_doc_id"] == "vec_001"


# --- invariant 10-11: rejected/pending cannot promote ---

def test_rejected_card_cannot_be_stored(tmp_path):
    import pytest
    store = _store(tmp_path)
    card = store.add(_valid_card())
    store.mark_rejected(card["id"])
    with pytest.raises(ValueError, match="rejected"):
        store.mark_stored(card["id"], vector_doc_id="vec_x")


def test_pending_card_cannot_be_stored(tmp_path):
    import pytest
    store = _store(tmp_path)
    card = store.add(_valid_card())
    with pytest.raises(ValueError, match="approved"):
        store.mark_stored(card["id"], vector_doc_id="vec_x")


# --- invariant 12: failed on vector write failure ---

def test_mark_failed_sets_storage_status(tmp_path):
    store = _store(tmp_path)
    card = store.add(_valid_card())
    store.mark_approved(card["id"])
    updated = store.mark_failed(card["id"], error="disk hatasi")
    assert updated["storage_status"] == "failed"
    assert updated["vector_doc_id"] is None


# --- JSONL persistence ---

def test_jsonl_append_one_line_per_card(tmp_path):
    store = _store(tmp_path)
    store.add(_valid_card(question="soru 1", answer="cevap 1", source_model="m1"))
    store.add(_valid_card(question="soru 2", answer="cevap 2", source_model="m2"))
    lines = (tmp_path / "knowledge_cards.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert obj["schema_version"] == "c1.6h"


def test_list_returns_all_cards(tmp_path):
    store = _store(tmp_path)
    store.add(_valid_card(question="q1", answer="a1", source_model="m1"))
    store.add(_valid_card(question="q2", answer="a2", source_model="m2"))
    cards = store.list_cards()
    assert len(cards) == 2


def test_get_returns_card_by_id(tmp_path):
    store = _store(tmp_path)
    card = store.add(_valid_card())
    found = store.get(card["id"])
    assert found is not None
    assert found["id"] == card["id"]


def test_get_returns_none_for_missing(tmp_path):
    store = _store(tmp_path)
    assert store.get("nonexistent") is None


def test_broken_jsonl_line_skipped(tmp_path):
    path = tmp_path / "knowledge_cards.jsonl"
    path.write_text('{"id":"ok","question":"q","answer":"a","source_model":"m","review_status":"pending","storage_status":"draft","vector_doc_id":null,"schema_version":"c1.6h","created_at":"2026-01-01T00:00:00","domain":"","tags":[],"confidence":80,"source_type":"answer_crystallization"}\n{not valid json}\n', encoding="utf-8")
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    cards = store.list_cards()
    assert len(cards) == 1
    assert cards[0]["id"] == "ok"
