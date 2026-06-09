"""C1.6H-1 - KnowledgeCardStore.

Append-only JSONL source-of-truth for crystallized knowledge cards.

Invariants (enforced):
- New cards: review_status=pending, storage_status=draft, vector_doc_id=null
- stored iff vector_doc_id is non-empty
- rejected/pending cards cannot be stored
- approved + failed write -> storage_status=failed, vector_doc_id stays null
- broken JSONL lines are skipped, not fatal

Scope (negative):
- No LLM calls
- No VectorMemory writes (caller's responsibility)
- No queue mutations
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "c1.6h"
DEFAULT_FILENAME = "knowledge_cards.jsonl"


class KnowledgeCardStore:
    """Append-only JSONL store for KnowledgeCards."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        self._root = Path(data_root) if data_root is not None else ROOT / "memory"
        self._root.mkdir(parents=True, exist_ok=True)
        self._path = self._root / DEFAULT_FILENAME

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, question: str, answer: str, source_model: str, confidence: int) -> None:
        if not str(question or "").strip():
            raise ValueError("question bos olamaz.")
        if not str(answer or "").strip():
            raise ValueError("answer bos olamaz.")
        if not str(source_model or "").strip():
            raise ValueError("source_model bos olamaz.")
        if not isinstance(confidence, int) or not (0 <= confidence <= 100):
            raise ValueError(f"confidence 0-100 arasinda olmali, verildi: {confidence!r}")

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def _append(self, card: dict[str, Any]) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")

    def _rewrite(self, cards: list[dict[str, Any]]) -> None:
        with self._path.open("w", encoding="utf-8") as f:
            for card in cards:
                f.write(json.dumps(card, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def list_cards(self) -> list[dict[str, Any]]:
        """Return all cards, skipping broken lines."""
        if not self._path.exists():
            return []
        cards = []
        for raw in self._path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                cards.append(json.loads(raw))
            except Exception:
                pass
        return cards

    def get(self, card_id: str) -> dict[str, Any] | None:
        """Return a card by id, or None."""
        card_id = str(card_id or "").strip()
        for card in self.list_cards():
            if card.get("id") == card_id:
                return card
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(
        self,
        question,
        answer: str = "",
        source_model: str = "",
        domain: str = "",
        tags: list[str] | None = None,
        confidence: int = 80,
    ) -> dict[str, Any]:
        """Create and persist a new KnowledgeCard (pending/draft)."""
        # Support dict-style call for convenience
        if isinstance(question, dict):
            d = question
            question = d.get("question", "")
            answer = d.get("answer", "")
            source_model = d.get("source_model", "")
            domain = d.get("domain", "")
            tags = d.get("tags", None)
            confidence = d.get("confidence", 80)

        question = str(question or "").strip()
        answer = str(answer or "").strip()
        source_model = str(source_model or "").strip()
        domain = str(domain or "").strip()
        tags = [str(t) for t in (tags or []) if t]
        if not isinstance(confidence, int):
            try:
                confidence = int(confidence)
            except Exception:
                confidence = 80

        self._validate(question, answer, source_model, confidence)

        card: dict[str, Any] = {
            "id": f"kc_{uuid.uuid4().hex[:12]}",
            "question": question,
            "answer": answer,
            "source_model": source_model,
            "source_type": "answer_crystallization",
            "domain": domain,
            "tags": tags,
            "confidence": confidence,
            "review_status": "pending",
            "storage_status": "draft",
            "vector_doc_id": None,
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._append(card)
        return card

    def _update(self, card_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a card in-place and rewrite JSONL."""
        cards = self.list_cards()
        updated = None
        for i, card in enumerate(cards):
            if card.get("id") == card_id:
                cards[i] = {**card, **updates}
                updated = cards[i]
                break
        if updated is None:
            raise ValueError(f"Kart bulunamadi: {card_id!r}")
        self._rewrite(cards)
        return updated

    def mark_approved(self, card_id: str) -> dict[str, Any]:
        """Set review_status=approved."""
        card = self.get(card_id)
        if card is None:
            raise ValueError(f"Kart bulunamadi: {card_id!r}")
        return self._update(card_id, {"review_status": "approved"})

    def mark_rejected(self, card_id: str) -> dict[str, Any]:
        """Set review_status=rejected."""
        card = self.get(card_id)
        if card is None:
            raise ValueError(f"Kart bulunamadi: {card_id!r}")
        return self._update(card_id, {"review_status": "rejected"})

    def mark_stored(self, card_id: str, vector_doc_id: str) -> dict[str, Any]:
        """Set storage_status=stored + vector_doc_id. Card must be approved."""
        vector_doc_id = str(vector_doc_id or "").strip()
        if not vector_doc_id:
            raise ValueError("vector_doc_id bos olamaz (storage_status=stored icin zorunlu).")

        card = self.get(card_id)
        if card is None:
            raise ValueError(f"Kart bulunamadi: {card_id!r}")

        review_status = str(card.get("review_status") or "")
        if review_status == "rejected":
            raise ValueError(f"rejected kart stored yapilamaz: {card_id!r}")
        if review_status != "approved":
            raise ValueError(f"Kart once approved olmali, simdi: {review_status!r}")

        return self._update(card_id, {
            "storage_status": "stored",
            "vector_doc_id": vector_doc_id,
        })

    def mark_failed(self, card_id: str, error: str = "") -> dict[str, Any]:
        """Set storage_status=failed (vector write failed). vector_doc_id stays null."""
        card = self.get(card_id)
        if card is None:
            raise ValueError(f"Kart bulunamadi: {card_id!r}")
        return self._update(card_id, {
            "storage_status": "failed",
            "vector_doc_id": None,
            "promotion_error": str(error or ""),
        })
