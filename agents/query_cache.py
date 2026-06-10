"""Y2-1 - QueryCache.

Exact-match local cache for question/answer pairs.
Prevents asking the same question to an external model twice.

Storage: memory/query_cache.json (dict, key = normalized question)

Scope (negative):
- No semantic similarity
- No VectorMemory
- No API calls
- No Telegram
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILENAME = "query_cache.json"


def _normalize(question: str) -> str:
    """Lowercase + strip for exact match key."""
    return str(question or "").strip().lower()


class QueryCache:
    """Exact-match query/answer cache backed by a JSON file."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        root = Path(data_root) if data_root is not None else ROOT / "memory"
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / DEFAULT_FILENAME

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_exact(self, question: str) -> dict[str, Any] | None:
        """Return cached entry for exact question, or None. Updates hit_count."""
        key = _normalize(question)
        if not key:
            return None
        data = self._load()
        if key not in data:
            return None
        entry = data[key]
        entry["hit_count"] = int(entry.get("hit_count") or 0) + 1
        entry["last_hit_at"] = datetime.now().isoformat(timespec="seconds")
        data[key] = entry
        self._save(data)
        return dict(entry)

    def put(
        self,
        question: str,
        answer: str,
        source_route: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store a question/answer pair. Overwrites if exists."""
        key = _normalize(question)
        if not key:
            return {"ok": False, "reason": "blank_question"}
        data = self._load()
        entry: dict[str, Any] = {
            "question": str(question).strip(),
            "answer": str(answer),
            "source_route": str(source_route or ""),
            "metadata": metadata or {},
            "hit_count": 0,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_hit_at": None,
        }
        data[key] = entry
        self._save(data)
        return {"ok": True, "key": key, "entry": entry}


    # ------------------------------------------------------------------
    # Semantic (token-overlap) match
    # ------------------------------------------------------------------

    _STOP_WORDS = {
        "mi", "mu", "ve", "ile", "bir", "bu", "su", "o",
        "da", "de", "ki", "ne", "ya", "ama", "fakat",
        "the", "a", "an", "is", "are", "was", "were",
        "in", "on", "at", "to", "for", "of", "and", "or",
    }

    _NEG_WORDS = {
        "degil", "yok", "hayir", "olmaz", "asla",
        "not", "no", "never",
    }

    def _tokenize(self, text: str) -> set[str]:
        import re
        # Include digits: "3070" != "4090" for hardware queries
        tokens = re.findall(r"[a-z0-9\u00e0-\u024f]+", text.lower())
        return {t for t in tokens if t not in self._STOP_WORDS and len(t) >= 2}

    def _overlap_score(self, a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _has_negation(self, tokens: set) -> bool:
        return bool(tokens & self._NEG_WORDS)

    def get_semantic(
        self,
        question: str,
        threshold: float = 0.80,
        min_common_tokens: int = 3,
    ) -> dict[str, Any] | None:
        """Return best semantic (token-overlap) match or None.

        Guards:
        1. Short query rule: if query < 3 meaningful tokens,
           require perfect overlap (score=1.0) to avoid false positives.
        2. Negation mismatch: if one side has negation tokens and the
           other does not, reject (prevents 'iyi' matching 'iyi degil').
        3. Digit-aware tokenizer: '3070' != '4090', hardware queries safe.
        """
        key = _normalize(question)
        if not key:
            return None

        q_tokens = self._tokenize(question)
        if not q_tokens:
            return None

        # Short query rule
        short_query = len(q_tokens) < 3
        effective_threshold = 1.0 if short_query else threshold
        effective_min = min(len(q_tokens), min_common_tokens) if short_query else min_common_tokens

        data = self._load()
        best_score = 0.0
        best_entry = None
        best_key = None

        q_has_neg = self._has_negation(q_tokens)

        for cached_key, entry in data.items():
            cached_q = str(entry.get("question") or cached_key)
            c_tokens = self._tokenize(cached_q)
            if not c_tokens:
                continue

            # Negation mismatch guard
            if q_has_neg != self._has_negation(c_tokens):
                continue

            score = self._overlap_score(q_tokens, c_tokens)
            common = len(q_tokens & c_tokens)

            if score >= effective_threshold and common >= effective_min and score > best_score:
                best_score = score
                best_entry = entry
                best_key = cached_key

        if best_entry is None:
            return None

        # Update hit count
        data[best_key]["hit_count"] = int(data[best_key].get("hit_count") or 0) + 1
        data[best_key]["last_hit_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        self._save(data)

        return {
            **best_entry,
            "match_type": "semantic",
            "similarity": round(best_score, 4),
            "matched_question": best_entry.get("question", best_key),
        }

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        data = self._load()
        total_hits = sum(int(e.get("hit_count") or 0) for e in data.values())
        return {
            "total_entries": len(data),
            "total_hits": total_hits,
        }
