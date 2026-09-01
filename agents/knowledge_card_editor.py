"""C1.9 - KnowledgeCardEditor.

Self-editing for KnowledgeCards with versioning.

Rules:
- Old card is NEVER deleted; marked superseded=True
- New card is a fresh pending/draft with previous_version_id
- Only safe fields can be changed: question, answer, domain, tags, confidence
- vector_doc_id, review_status, storage_status, id etc. are immutable via edit
- Vector update is a separate promote step (same as C1.6H-3)

Scope (negative):
- No VectorMemory writes
- No automatic approval
- No Telegram
- No candidate edits
"""
from __future__ import annotations

from typing import Any

_SAFE_FIELDS = frozenset({"question", "answer", "domain", "tags", "confidence", "source_model"})


class KnowledgeCardEditor:
    """Edit a KnowledgeCard by creating a new versioned card."""

    def __init__(self, store=None, data_root=None) -> None:
        self._store = store
        self._data_root = data_root

    def _get_store(self):
        if self._store is not None:
            return self._store
        from pathlib import Path
        from agents.knowledge_card_store import KnowledgeCardStore
        root = self._data_root or Path(__file__).resolve().parents[1] / "memory"
        self._store = KnowledgeCardStore(data_root=root)
        return self._store

    def edit(self, card_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Create a new version of a card with applied changes.

        Returns {ok, new_card, old_card_id} or {ok, reason}.
        """
        store = self._get_store()

        old = store.get(card_id)
        if old is None:
            return {"ok": False, "reason": "card_not_found", "card_id": card_id}

        if not changes:
            return {"ok": False, "reason": "no_changes", "card_id": card_id}

        safe_changes = {k: v for k, v in changes.items() if k in _SAFE_FIELDS}
        if not safe_changes:
            return {"ok": False, "reason": "no_safe_changes", "card_id": card_id}

        # Build new card fields from old + safe changes
        new_question = str(safe_changes.get("question") or old.get("question") or "").strip()
        new_answer = str(safe_changes.get("answer") or old.get("answer") or "").strip()
        new_source_model = str(safe_changes.get("source_model") or old.get("source_model") or "").strip()
        new_domain = str(safe_changes.get("domain", old.get("domain", "")) or "")
        new_tags = safe_changes.get("tags", old.get("tags", []))
        new_confidence = safe_changes.get("confidence", old.get("confidence", 80))

        new_card = store.add(
            question=new_question,
            answer=new_answer,
            source_model=new_source_model,
            domain=new_domain,
            tags=new_tags,
            confidence=new_confidence,
        )

        # Stamp previous_version_id on new card
        store._update(new_card["id"], {"previous_version_id": card_id})
        new_card["previous_version_id"] = card_id

        # Mark old card superseded
        store.mark_superseded(card_id, superseded_by=new_card["id"])

        return {
            "ok": True,
            "new_card": new_card,
            "old_card_id": card_id,
        }
