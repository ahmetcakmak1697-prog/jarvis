"""C1.6H-5 - KnowledgeCardRetriever.

Retrieval-first lookup: before calling an expensive model,
check if a stored+approved KnowledgeCard answers the question.

Matching strategy: simple keyword overlap (case-insensitive, Turkish-folded).
No LLM, no vector search ? fast and deterministic.

Scope (negative):
- No LLM calls
- No VectorMemory reads (keyword match on JSONL store)
- No queue mutations
- No side effects
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _tr_fold(s: str) -> str:
    s = s.replace("\u0130", "i").replace("\u0049", "i").replace("\u0131", "i")
    s = s.replace("\u015f", "s").replace("\u015e", "s")
    s = s.replace("\u011f", "g").replace("\u011e", "g")
    s = s.replace("\u00fc", "u").replace("\u00dc", "u")
    s = s.replace("\u00f6", "o").replace("\u00d6", "o")
    s = s.replace("\u00e7", "c").replace("\u00c7", "c")
    return s.lower()


def _tokens(text: str) -> set[str]:
    folded = _tr_fold(str(text or ""))
    return {t for t in folded.split() if len(t) >= 3}


class KnowledgeCardRetriever:
    """Find a stored+approved KnowledgeCard that matches a question."""

    def __init__(
        self,
        store=None,
        data_root: Path | str | None = None,
        min_confidence: int = 50,
    ) -> None:
        self._store = store
        self._data_root = Path(data_root) if data_root is not None else ROOT / "memory"
        self.min_confidence = min_confidence

    def _get_store(self):
        if self._store is not None:
            return self._store
        from agents.knowledge_card_store import KnowledgeCardStore
        self._store = KnowledgeCardStore(data_root=self._data_root)
        return self._store

    def _is_eligible(self, card: dict) -> bool:
        return (
            str(card.get("review_status") or "") == "approved"
            and str(card.get("storage_status") or "") == "stored"
            and int(card.get("confidence") or 0) >= self.min_confidence
        )

    def _score(self, query_tokens: set, card: dict) -> int:
        card_tokens = _tokens(card.get("question", ""))
        return len(query_tokens & card_tokens)

    def lookup(self, question: str) -> dict[str, Any]:
        """Return best matching card or not-found result. No side effects."""
        query_tokens = _tokens(question)
        store = self._get_store()
        cards = store.list_cards()

        best_card = None
        best_score = 0

        for card in cards:
            if not self._is_eligible(card):
                continue
            score = self._score(query_tokens, card)
            if score > best_score:
                best_score = score
                best_card = card

        if best_card is None or best_score == 0:
            return {
                "found": False,
                "answer": None,
                "card": None,
                "source_model": None,
                "score": 0,
            }

        return {
            "found": True,
            "answer": str(best_card.get("answer") or ""),
            "card": best_card,
            "source_model": str(best_card.get("source_model") or ""),
            "score": best_score,
        }
