"""C1.6H-3 - KnowledgeCardPromoter.

Promotes an approved KnowledgeCard into VectorMemory.

Safety rules:
- Card must be approved before promotion
- vector_doc_id set only after successful VectorMemory.remember()
- Failed write -> storage_status=failed, vector_doc_id stays null
- Already stored cards are not re-promoted
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeCardPromoter:
    """Promote an approved KnowledgeCard into VectorMemory."""

    def __init__(
        self,
        store=None,
        memory=None,
        data_root: Path | str | None = None,
    ) -> None:
        self._store = store
        self._memory = memory
        self._data_root = Path(data_root) if data_root is not None else ROOT / "memory"

    def _get_store(self):
        if self._store is not None:
            return self._store
        from agents.knowledge_card_store import KnowledgeCardStore
        self._store = KnowledgeCardStore(data_root=self._data_root)
        return self._store

    def _get_memory(self):
        if self._memory is not None:
            return self._memory
        from tools.vector_memory import VectorMemory
        self._memory = VectorMemory()
        return self._memory

    def promote(self, card_id: str) -> dict[str, Any]:
        """Promote card to VectorMemory. Returns result dict."""
        card_id = str(card_id or "").strip()
        store = self._get_store()

        card = store.get(card_id)
        if card is None:
            return {"ok": False, "promoted": False, "reason": "card_not_found", "card_id": card_id}

        review_status = str(card.get("review_status") or "")
        storage_status = str(card.get("storage_status") or "")

        if storage_status == "stored":
            return {"ok": False, "promoted": False, "reason": "already_stored", "card_id": card_id}

        if review_status != "approved":
            return {"ok": False, "promoted": False, "reason": "not_approved", "card_id": card_id}

        question = str(card.get("question") or "").strip()
        answer = str(card.get("answer") or "").strip()

        meta = {
            "source": "knowledge_card_promoter",
            "source_type": "answer_crystallization",
            "card_id": card_id,
            "schema_version": card.get("schema_version", "c1.6h"),
            "domain": str(card.get("domain") or ""),
            "tags": ",".join(list(card.get("tags") or [])) or "none",
            "confidence": card.get("confidence"),
            "source_model": str(card.get("source_model") or ""),
            "created_at": str(card.get("created_at") or ""),
        }

        memory = self._get_memory()
        vector_doc_id = memory.remember(question, answer, meta)

        if not vector_doc_id:
            store.mark_failed(card_id, error="VectorMemory.remember() returned empty doc_id")
            return {"ok": False, "promoted": False, "reason": "vector_write_failed", "card_id": card_id}

        updated = store.mark_stored(card_id, vector_doc_id=vector_doc_id)
        return {
            "ok": True,
            "promoted": True,
            "reason": "promoted",
            "card_id": card_id,
            "vector_doc_id": vector_doc_id,
            "card": updated,
        }
