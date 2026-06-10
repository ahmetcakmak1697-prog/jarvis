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

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        data = self._load()
        total_hits = sum(int(e.get("hit_count") or 0) for e in data.values())
        return {
            "total_entries": len(data),
            "total_hits": total_hits,
        }
