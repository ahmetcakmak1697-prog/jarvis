"""Memory Candidate Queue - D1.6.

Stores web research / idle learning outputs as reviewable memory candidates.

Rule:
- web research must not enter long-term memory silently
- every candidate needs explicit user decision before memory write
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class MemoryCandidate:
    id: str
    created_at: str
    source_type: str
    mode: str
    status: str
    query: str
    summary: str
    confidence: int
    tier: str
    source_urls: list[str]
    source_scores: list[dict[str, Any]]
    retrieved_at: str
    expires_at: str | None
    tags: list[str]
    user_decision: str | None = None
    decided_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryCandidateQueue:
    """Append-only-ish local queue for candidate memory items."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.path = self.root / "memory" / "memory_candidates.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add_web_candidate(
        self,
        query: str,
        research_text: str,
        source_scores: list[dict[str, Any]] | None = None,
        mode: str = "sync",
        ttl_days: int | None = 60,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        source_scores = source_scores or []
        tags = tags or ["web_research"]

        summary = self._build_summary(research_text)
        source_urls = self._extract_urls(research_text, source_scores)
        confidence = self._confidence_from_sources(source_scores, research_text)
        tier = self._tier_from_confidence(confidence)

        now = datetime.now()
        expires_at = None
        if ttl_days:
            expires_at = (now + timedelta(days=ttl_days)).isoformat(timespec="seconds")

        candidate = MemoryCandidate(
            id=self._make_id(query, summary),
            created_at=now.isoformat(timespec="seconds"),
            source_type="web_research",
            mode=mode,
            status="pending_review",
            query=query.strip(),
            summary=summary,
            confidence=confidence,
            tier=tier,
            source_urls=source_urls,
            source_scores=source_scores,
            retrieved_at=now.isoformat(timespec="seconds"),
            expires_at=expires_at,
            tags=tags,
        )

        items = self._load()
        existing_ids = {item.get("id") for item in items if isinstance(item, dict)}

        if candidate.id not in existing_ids:
            items.append(candidate.to_dict())
            self._save(items)

        return candidate.to_dict()

    def list_pending(self, limit: int = 10) -> list[dict[str, Any]]:
        items = self._load()
        pending = [
            item for item in items
            if isinstance(item, dict) and item.get("status") == "pending_review"
        ]
        return pending[-limit:]

    def decide(self, candidate_id: str, decision: str) -> dict[str, Any]:
        """Mark candidate as approved/rejected/deferred.

        This does not write to vector memory. It only records user decision.
        Actual memory write will be wired later through MemoryPolicy.
        """
        decision = (decision or "").strip().lower()
        allowed = {"approved", "rejected", "deferred"}

        if decision not in allowed:
            return {
                "ok": False,
                "error": "decision approved/rejected/deferred olmali.",
                "candidate_id": candidate_id,
            }

        items = self._load()
        for item in items:
            if item.get("id") == candidate_id:
                item["status"] = decision
                item["user_decision"] = decision
                item["decided_at"] = datetime.now().isoformat(timespec="seconds")
                self._save(items)
                return {"ok": True, "candidate": item}

        return {
            "ok": False,
            "error": "candidate bulunamadi.",
            "candidate_id": candidate_id,
        }

    def stats(self) -> dict[str, Any]:
        items = self._load()
        counts: dict[str, int] = {}

        for item in items:
            if not isinstance(item, dict):
                continue
            status = item.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1

        return {
            "path": str(self.path),
            "total": len(items),
            "counts": counts,
            "pending": counts.get("pending_review", 0),
        }

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except Exception:
            pass

        return []

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _make_id(self, query: str, summary: str) -> str:
        raw = f"{query}|{summary}".encode("utf-8", errors="ignore")
        return "mc_" + hashlib.sha256(raw).hexdigest()[:16]

    def _build_summary(self, research_text: str) -> str:
        text = (research_text or "").strip()

        if not text:
            return "Ara?t?rma sonucu bo? d?nd?."

        # Remove excessive whitespace while keeping core meaning.
        text = " ".join(text.split())

        # Keep summary candidate short and reviewable.
        if len(text) > 700:
            text = text[:700].rstrip() + "..."

        return text

    def _extract_urls(
        self,
        research_text: str,
        source_scores: list[dict[str, Any]],
    ) -> list[str]:
        urls = []

        for item in source_scores:
            url = str(item.get("url") or "").strip()
            if url:
                urls.append(url)

        # Fallback: simple URL extraction from formatted research text.
        import re
        urls.extend(re.findall(r"https?://[^\s]+", research_text or ""))

        clean = []
        for url in urls:
            url = url.rstrip(".,);]")
            if url and url not in clean:
                clean.append(url)

        return clean[:10]

    def _confidence_from_sources(
        self,
        source_scores: list[dict[str, Any]],
        research_text: str,
    ) -> int:
        scores = [
            int(item.get("score", 0) or 0)
            for item in source_scores
            if isinstance(item, dict)
        ]

        if scores:
            return max(0, min(100, int(sum(scores) / len(scores))))

        # Fallback: formatted research text contains confidence markers.
        if "G?ven: high" in research_text or "Guven: high" in research_text:
            return 80
        if "G?ven: medium" in research_text or "Guven: medium" in research_text:
            return 60
        if "G?ven:" in research_text or "Guven:" in research_text:
            return 45

        return 40

    def _tier_from_confidence(self, confidence: int) -> str:
        if confidence >= 80:
            return "long_term_candidate"
        if confidence >= 60:
            return "project_or_session_candidate"
        if confidence >= 40:
            return "temporary_candidate"
        return "low_confidence"


if __name__ == "__main__":
    q = MemoryCandidateQueue()

    sample = """[1] OpenAI API Pricing
Kaynak: TEST | https://openai.com/api/pricing
G?ven: high / 100
G?ven nedeni: high_trust_domain, documentation_or_research_signal
?zet: Official documentation and current API pricing information for models."""

    c = q.add_web_candidate(
        query="OpenAI API fiyatlar? 2026",
        research_text=sample,
        source_scores=[
            {
                "url": "https://openai.com/api/pricing",
                "score": 100,
                "tier": "high",
                "reasons": ["high_trust_domain"],
            }
        ],
        mode="sync",
        ttl_days=30,
    )

    print(c)
    print(q.stats())
