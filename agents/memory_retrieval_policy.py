"""Memory Retrieval Policy - C1.4.

Filters vector memory recall results before they enter the LLM context.

This module does not query ChromaDB by itself. It only receives candidate
memory hits from VectorMemory.find_similar() and returns safe, bounded results.

C1.4 principles:
- no sensitive/review/expired memory in normal answer context
- no low-quality or irrelevant memory flood
- prefer semantic/approved long-term records
- keep context small and predictable
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RetrievalDecision:
    allowed: bool
    reason: str
    score: float
    memory_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryRetrievalPolicy:
    """Apply safe retrieval rules to vector memory hits."""

    BLOCKED_ACTIONS = {
        "ignore",
        "temporary",
        "sensitive_review",
    }

    BLOCKED_MEMORY_TYPES = {
        "sensitive_review",
        "ignore",
    }

    BLOCKED_STORAGE_TARGETS = {
        "review_queue",
        "temporary_json",
        "none",
    }

    BLOCKED_STATUSES = {
        "pending_review",
        "rejected",
        "deferred",
        "expired",
        "blocked",
    }

    BLOCKED_SENSITIVITY = {
        "sensitive",
        "secret",
    }

    def __init__(
        self,
        max_items: int = 5,
        min_similarity: float = 0.70,
        allow_personal: bool = True,
    ):
        self.max_items = max(1, int(max_items))
        self.min_similarity = float(min_similarity)
        self.allow_personal = bool(allow_personal)

    def filter_hits(self, hits: list[dict[str, Any]], query: str = "") -> list[dict[str, Any]]:
        """Return safe bounded memory hits.

        Input hit shape is intentionally loose because VectorMemory currently
        returns plain dicts. We preserve original hits and attach retrieval_meta.
        """
        safe: list[dict[str, Any]] = []

        for hit in hits or []:
            decision = self.decide_hit(hit, query=query)
            if not decision.allowed:
                continue

            out = dict(hit)
            out["retrieval_meta"] = decision.to_dict()
            safe.append(out)

        safe.sort(
            key=lambda item: float((item.get("retrieval_meta") or {}).get("score", 0.0)),
            reverse=True,
        )
        return safe[: self.max_items]

    def decide_hit(self, hit: dict[str, Any], query: str = "") -> RetrievalDecision:
        if not isinstance(hit, dict):
            return RetrievalDecision(False, "not_a_dict", 0.0)

        meta = self._metadata(hit)

        memory_id = str(hit.get("id") or meta.get("id") or meta.get("candidate_id") or "") or None
        similarity = self._similarity(hit)

        if similarity is not None and similarity < self.min_similarity:
            return RetrievalDecision(False, "below_similarity_threshold", similarity, memory_id)

        action = str(meta.get("memory_action") or meta.get("action") or "").strip()
        if action in self.BLOCKED_ACTIONS:
            return RetrievalDecision(False, f"blocked_action:{action}", similarity or 0.0, memory_id)

        memory_type = str(meta.get("memory_type") or "").strip()
        if memory_type in self.BLOCKED_MEMORY_TYPES:
            return RetrievalDecision(False, f"blocked_memory_type:{memory_type}", similarity or 0.0, memory_id)

        storage_target = str(meta.get("storage_target") or "").strip()
        if storage_target in self.BLOCKED_STORAGE_TARGETS:
            return RetrievalDecision(False, f"blocked_storage_target:{storage_target}", similarity or 0.0, memory_id)

        status = str(meta.get("status") or meta.get("candidate_status") or "").strip()
        if status in self.BLOCKED_STATUSES:
            return RetrievalDecision(False, f"blocked_status:{status}", similarity or 0.0, memory_id)

        sensitivity = str(meta.get("sensitivity") or "").strip()
        if sensitivity in self.BLOCKED_SENSITIVITY:
            return RetrievalDecision(False, f"blocked_sensitivity:{sensitivity}", similarity or 0.0, memory_id)

        if sensitivity == "personal" and not self.allow_personal:
            return RetrievalDecision(False, "personal_not_allowed", similarity or 0.0, memory_id)

        if meta.get("requires_review") is True:
            return RetrievalDecision(False, "requires_review", similarity or 0.0, memory_id)

        if meta.get("allow_vector") is False and action:
            return RetrievalDecision(False, "vector_not_allowed", similarity or 0.0, memory_id)

        score = self._score(hit, meta, similarity)
        return RetrievalDecision(True, "allowed", score, memory_id)

    def _metadata(self, hit: dict[str, Any]) -> dict[str, Any]:
        meta = hit.get("metadata")
        if isinstance(meta, dict):
            return meta

        # Some older code may flatten metadata into the hit itself.
        return hit

    def _similarity(self, hit: dict[str, Any]) -> float | None:
        for key in ("similarity", "score", "distance_score"):
            value = hit.get(key)
            try:
                if value is not None:
                    return float(value)
            except Exception:
                continue

        distance = hit.get("distance")
        try:
            if distance is not None:
                # Chroma cosine distance: lower is better. Convert rough similarity.
                return max(0.0, min(1.0, 1.0 - float(distance)))
        except Exception:
            pass

        return None

    def _score(self, hit: dict[str, Any], meta: dict[str, Any], similarity: float | None) -> float:
        score = similarity if similarity is not None else 0.75

        try:
            importance = float(meta.get("memory_importance") or meta.get("importance") or 0)
            score += min(0.20, importance / 100.0)
        except Exception:
            pass

        tags = meta.get("memory_tags") or meta.get("tags") or []
        if isinstance(tags, str):
            tags_text = tags
        else:
            tags_text = ",".join(str(t) for t in tags)

        if "explicit_save" in tags_text:
            score += 0.05
        if "project" in tags_text:
            score += 0.05
        if str(meta.get("memory_action") or meta.get("action") or "") == "keep_long_term":
            score += 0.05

        return max(0.0, min(1.0, score))


if __name__ == "__main__":
    policy = MemoryRetrievalPolicy()
    hits = [
        {
            "id": "m1",
            "similarity": 0.91,
            "metadata": {
                "memory_action": "keep_long_term",
                "memory_type": "semantic",
                "storage_target": "vector",
                "sensitivity": "normal",
                "memory_tags": "explicit_save,project",
                "memory_importance": 9,
            },
        },
        {
            "id": "m2",
            "similarity": 0.95,
            "metadata": {
                "memory_action": "sensitive_review",
                "sensitivity": "sensitive",
            },
        },
    ]

    for item in policy.filter_hits(hits):
        print(item)
