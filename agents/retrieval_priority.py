"""C1.7 - RetrievalPriorityRanker.

Re-ranks memory hits from MemoryRetrievalPolicy using:
  - similarity (from vector search)
  - tier bonus (core > recall > archival > episodic)
  - maturity_score (from MemoryMaturityScorer)
  - importance

Does NOT replace MemoryRetrievalPolicy. Input = already-filtered hits.
priority_score is added at top level of each output hit (not nested in metadata).

Scope (negative):
- No VectorMemory writes/reads
- No file writes
- No queue mutations
- No Telegram commands
- Input hits are never mutated (deepcopy before modification)
"""
from __future__ import annotations

import copy
from typing import Any

_TIER_BONUS = {
    "core": 0.20,
    "recall": 0.10,
    "archival": 0.05,
    "episodic": 0.00,
}


class RetrievalPriorityRanker:
    """Re-rank filtered memory hits by combined priority score."""

    def __init__(self, max_items: int = 5) -> None:
        self.max_items = max(1, int(max_items))

    def _meta(self, hit: dict) -> dict:
        m = hit.get("metadata")
        return m if isinstance(m, dict) else hit

    def _similarity(self, hit: dict) -> float:
        for key in ("similarity", "score"):
            v = hit.get(key)
            try:
                if v is not None:
                    return max(0.0, min(1.0, float(v)))
            except Exception:
                pass
        return 0.75

    def _priority(self, hit: dict) -> float:
        meta = self._meta(hit)

        similarity = self._similarity(hit)

        tier = str(meta.get("tier") or "recall").lower()
        tier_bonus = _TIER_BONUS.get(tier, 0.0)

        maturity_raw = meta.get("maturity_score")
        try:
            maturity_bonus = min(0.15, float(maturity_raw or 0) / 100.0 * 0.15)
        except Exception:
            maturity_bonus = 0.0

        try:
            importance = float(meta.get("memory_importance") or meta.get("importance") or 0)
            importance_bonus = min(0.10, importance / 100.0)
        except Exception:
            importance_bonus = 0.0

        score = similarity + tier_bonus + maturity_bonus + importance_bonus
        return max(0.0, min(1.0, score))

    def rank(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return re-ranked hits with priority_score at top level.

        Input hits are never mutated.
        """
        if not hits:
            return []

        scored = []
        for hit in hits:
            out = copy.deepcopy(hit)
            out["priority_score"] = float(round(self._priority(hit), 4))
            scored.append(out)

        scored.sort(key=lambda h: h["priority_score"], reverse=True)
        return scored[: self.max_items]
