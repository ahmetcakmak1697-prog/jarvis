"""C1.9 KnowledgeCard self-edit (versioning) tests."""
from __future__ import annotations
from agents.knowledge_card_store import KnowledgeCardStore


def _store(tmp_path):
    return KnowledgeCardStore(data_root=tmp_path)


def _approved_card(store):
    card = store.add(
        question="Eski soru?",
        answer="Eski cevap.",
        source_model="claude-opus-4",
        confidence=80,
    )
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="vec_old_001")
    return store.get(card["id"])


def test_edit_creates_new_version(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    result = editor.edit(old["id"], {"answer": "Yeni duzeltilmis cevap."})
    assert result["ok"] is True
    assert result["new_card"]["answer"] == "Yeni duzeltilmis cevap."
    assert result["new_card"]["id"] != old["id"]


def test_edit_preserves_old_card(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    editor.edit(old["id"], {"answer": "Yeni cevap."})
    still_there = store.get(old["id"])
    assert still_there is not None
    assert still_there["answer"] == "Eski cevap."


def test_edit_marks_old_superseded(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    editor.edit(old["id"], {"answer": "Yeni cevap."})
    updated_old = store.get(old["id"])
    assert updated_old.get("superseded") is True


def test_new_card_has_previous_version_id(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    result = editor.edit(old["id"], {"answer": "Yeni cevap."})
    assert result["new_card"].get("previous_version_id") == old["id"]


def test_new_card_is_pending_draft(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    result = editor.edit(old["id"], {"answer": "Yeni cevap."})
    new = result["new_card"]
    assert new["review_status"] == "pending"
    assert new["storage_status"] == "draft"
    assert new["vector_doc_id"] is None


def test_edit_rejects_unknown_card(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    editor = KnowledgeCardEditor(store=store)
    result = editor.edit("nonexistent_id", {"answer": "x"})
    assert result["ok"] is False
    assert result["reason"] == "card_not_found"


def test_edit_rejects_empty_changes(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    result = editor.edit(old["id"], {})
    assert result["ok"] is False
    assert result["reason"] == "no_changes"


def test_edit_only_allows_safe_fields(tmp_path):
    from agents.knowledge_card_editor import KnowledgeCardEditor
    store = _store(tmp_path)
    old = _approved_card(store)
    editor = KnowledgeCardEditor(store=store)
    result = editor.edit(old["id"], {"vector_doc_id": "hack", "review_status": "approved"})
    assert result["ok"] is False
    assert result["reason"] == "no_safe_changes"
