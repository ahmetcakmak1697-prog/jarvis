"""C1.6H-5 - KnowledgeCardRetriever (v2 - Jaccard precision).

Matching strategy: Jaccard token-overlap with guards:
  - digit-aware tokenizer (RTX 3070 != RTX 4090)
  - stop-word filter
  - negation mismatch guard (iyi != iyi degil)
  - short-query rule (< 3 tokens -> perfect overlap)
  - threshold: 0.80, min_common_tokens: 3
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_STOP = {
    "mi", "mu", "ve", "ile", "bir", "bu", "su", "o",
    "da", "de", "ki", "ne", "ya", "ama", "fakat", "icin",
    "nasil", "how",
    "the", "a", "an", "is", "are", "was", "in", "on", "at",
    "to", "for", "of", "and", "or",
}

_NEG = {
    "degil", "yok", "hayir", "olmaz", "asla",
    "not", "no", "never",
}


def _tr_fold(s: str) -> str:
    s = s.replace("\u0130", "i").replace("\u0049", "i").replace("\u0131", "i")
    s = s.replace("\u015f", "s").replace("\u015e", "s")
    s = s.replace("\u011f", "g").replace("\u011e", "g")
    s = s.replace("\u00fc", "u").replace("\u00dc", "u")
    s = s.replace("\u00f6", "o").replace("\u00d6", "o")
    s = s.replace("\u00e7", "c").replace("\u00c7", "c")
    return s.lower()


def _tokens(text: str) -> set:
    folded = _tr_fold(str(text or ""))
    raw = re.findall(r"[a-z0-9\u00e0-\u024f]+", folded)
    return {t for t in raw if t not in _STOP and len(t) >= 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class KnowledgeCardRetriever:
    """Find a stored+approved KnowledgeCard that matches a question."""

    DEFAULT_THRESHOLD = 0.80
    DEFAULT_MIN_COMMON = 3

    def __init__(
        self,
        store=None,
        data_root=None,
        min_confidence: int = 50,
        threshold: float = 0.80,
        min_common_tokens: int = 3,
    ) -> None:
        self._store = store
        self._data_root = Path(data_root) if data_root is not None else ROOT / "memory"
        self.min_confidence = min_confidence
        self.threshold = threshold
        self.min_common_tokens = min_common_tokens

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
            and not card.get("superseded", False)
            and int(card.get("confidence") or 0) >= self.min_confidence
        )

    def _score(self, query_tokens: set, card: dict) -> float:
        card_tokens = _tokens(card.get("question", ""))
        if not card_tokens:
            return 0.0
        q_neg = bool(query_tokens & _NEG)
        c_neg = bool(card_tokens & _NEG)
        if q_neg != c_neg:
            return 0.0
        score = _jaccard(query_tokens, card_tokens)
        common = len(query_tokens & card_tokens)
        qt_len = len(query_tokens)
        eff_threshold = 1.0 if qt_len < 3 else self.threshold
        eff_min = min(qt_len, self.min_common_tokens) if qt_len < 3 else self.min_common_tokens
        if score >= eff_threshold and common >= eff_min:
            return score
        return 0.0

    def lookup(self, question: str) -> dict:
        """Return best matching card or not-found result. No side effects."""
        query_tokens = _tokens(question)
        store = self._get_store()
        cards = store.list_cards()
        best_card = None
        best_score = 0.0
        for card in cards:
            if not self._is_eligible(card):
                continue
            score = self._score(query_tokens, card)
            if score > best_score:
                best_score = score
                best_card = card
        if best_card is None or best_score == 0.0:
            return {"found": False, "answer": None, "card": None, "source_model": None, "score": 0.0}
        return {
            "found": True,
            "answer": str(best_card.get("answer") or ""),
            "card": best_card,
            "source_model": str(best_card.get("source_model") or ""),
            "score": round(best_score, 4),
        }
