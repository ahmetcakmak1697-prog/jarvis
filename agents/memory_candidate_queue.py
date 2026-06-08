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

from agents.audit_logger import AuditLogger


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
        self.audit = AuditLogger(self.root)

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

            self.audit.log(
                event="web_candidate_queued",
                query=query,
                candidate_id=candidate.id,
                action="queued",
                payload={
                    "source_type": candidate.source_type,
                    "mode": candidate.mode,
                    "status": candidate.status,
                    "confidence": candidate.confidence,
                    "tier": candidate.tier,
                    "source_urls": candidate.source_urls,
                    "expires_at": candidate.expires_at,
                    "tags": candidate.tags,
                },
            )

        return candidate.to_dict()

    def add_conversation_candidate(
        self,
        user_msg: str,
        jarvis_msg: str = "",
        route: dict[str, Any] | None = None,
        mode: str = "conversation",
        ttl_days: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Queue a conversation-derived memory candidate for user review.

        C1.2A:
        - no silent semantic/vector write
        - ignored/temporary/daily-summary routes are not queued here
        - sensitive routes go to the same review queue
        """
        from agents.memory_schema import MemorySchemaMapper

        user_msg = (user_msg or "").strip()
        jarvis_msg = (jarvis_msg or "").strip()

        if not user_msg and not jarvis_msg:
            return {
                "ok": False,
                "queued": False,
                "reason": "empty_exchange",
            }

        if route is None:
            route = MemorySchemaMapper().route_exchange(
                user_msg=user_msg,
                jarvis_msg=jarvis_msg,
                meta={"source": "conversation"},
            ).to_dict()

        memory_type = str(route.get("memory_type") or "")
        storage_target = str(route.get("storage_target") or "")

        should_queue = (
            (memory_type == "semantic" and storage_target == "vector")
            or memory_type == "sensitive_review"
            or storage_target == "review_queue"
            or bool(route.get("requires_review"))
        )

        if not should_queue:
            return {
                "ok": True,
                "queued": False,
                "reason": "route_not_review_candidate",
                "route": route,
            }

        now = datetime.now()
        if ttl_days is None:
            ttl_days = 60 if memory_type != "sensitive_review" else 14

        expires_at = None
        if ttl_days:
            expires_at = (now + timedelta(days=ttl_days)).isoformat(timespec="seconds")

        base_tags = ["conversation", "c1_2_review"]
        route_tags = list(route.get("tags") or [])
        merged_tags = list(dict.fromkeys(base_tags + route_tags + (tags or [])))

        summary_parts = []
        if user_msg:
            summary_parts.append(f"USER: {user_msg}")
        if jarvis_msg:
            summary_parts.append(f"JARVIS: {jarvis_msg}")
        summary = "\n".join(summary_parts).strip()

        if len(summary) > 1200:
            summary = summary[:1200].rstrip() + "..."

        confidence = int(route.get("confidence") or 50)
        tier = self._tier_from_confidence(confidence)

        candidate = MemoryCandidate(
            id=self._make_id(user_msg or "conversation", summary),
            created_at=now.isoformat(timespec="seconds"),
            source_type="conversation",
            mode=mode,
            status="pending_review",
            query=user_msg[:500],
            summary=summary,
            confidence=confidence,
            tier=tier,
            source_urls=[],
            source_scores=[],
            retrieved_at=now.isoformat(timespec="seconds"),
            expires_at=expires_at,
            tags=merged_tags,
        )

        item = candidate.to_dict()
        item["route"] = route
        item["schema_version"] = route.get("schema_version", "c1.1")
        item["memory_type"] = memory_type
        item["storage_target"] = storage_target
        item["sensitivity"] = route.get("sensitivity")
        item["delete_id"] = route.get("delete_id")

        items = self._load()
        existing_ids = {entry.get("id") for entry in items if isinstance(entry, dict)}

        if candidate.id not in existing_ids:
            items.append(item)
            self._save(items)

            self.audit.log(
                event="conversation_candidate_queued",
                query=user_msg,
                candidate_id=candidate.id,
                action="queued",
                payload={
                    "source_type": candidate.source_type,
                    "mode": candidate.mode,
                    "status": candidate.status,
                    "confidence": candidate.confidence,
                    "tier": candidate.tier,
                    "expires_at": candidate.expires_at,
                    "tags": candidate.tags,
                    "memory_type": memory_type,
                    "storage_target": storage_target,
                    "sensitivity": route.get("sensitivity"),
                    "delete_id": route.get("delete_id"),
                },
            )

        return {
            "ok": True,
            "queued": True,
            "candidate": item,
            "route": route,
        }

    def add_synthesis_candidate(
        self,
        proposal: dict[str, Any],
        ttl_days: int | None = 60,
    ) -> dict[str, Any]:
        """Queue a synthesized memory proposal for review.

        C1.6D:
        - takes C1.6C proposal output
        - writes only to review queue
        - never writes directly to vector/long-term memory
        """
        if not isinstance(proposal, dict):
            return {
                "ok": False,
                "queued": False,
                "reason": "invalid_proposal",
            }

        if proposal.get("proposal_type") != "synthesized_memory":
            return {
                "ok": False,
                "queued": False,
                "reason": "invalid_proposal_type",
            }

        theme = str(proposal.get("theme") or "").strip()
        summary = str(proposal.get("summary") or "").strip()
        if not theme or not summary:
            return {
                "ok": False,
                "queued": False,
                "reason": "missing_theme_or_summary",
            }

        try:
            confidence = int(proposal.get("confidence") or 50)
        except (TypeError, ValueError):
            confidence = 50
        confidence = max(0, min(100, confidence))

        try:
            source_count = int(proposal.get("source_count") or 0)
        except (TypeError, ValueError):
            source_count = 0

        source_ids = proposal.get("source_ids") or []
        if not isinstance(source_ids, list):
            source_ids = []

        now = datetime.now()
        expires_at = None
        if ttl_days:
            expires_at = (now + timedelta(days=ttl_days)).isoformat(timespec="seconds")

        query = f"synthesis:{theme}"
        tags = list(dict.fromkeys([
            "synthesis",
            "c1_6",
            f"theme:{theme}",
        ]))

        candidate = MemoryCandidate(
            id=self._make_id(query, summary),
            created_at=now.isoformat(timespec="seconds"),
            source_type="synthesis",
            mode="memory_synthesis",
            status="pending_review",
            query=query,
            summary=summary,
            confidence=confidence,
            tier=self._tier_from_confidence(confidence),
            source_urls=[],
            source_scores=[],
            retrieved_at=now.isoformat(timespec="seconds"),
            expires_at=expires_at,
            tags=tags,
        )

        item = candidate.to_dict()
        item["schema_version"] = "c1.6d"
        item["memory_type"] = "semantic"
        item["storage_target"] = "review_queue"
        item["sensitivity"] = "normal"
        item["proposal_type"] = "synthesized_memory"
        item["theme"] = theme
        item["source_count"] = source_count
        item["source_ids"] = [str(source_id) for source_id in source_ids]
        item["route"] = {
            "schema_version": "c1.6d",
            "memory_type": "semantic",
            "storage_target": "review_queue",
            "sensitivity": "normal",
            "requires_review": True,
            "allow_vector": False,
            "allow_daily_summary": True,
            "tags": tags,
            "confidence": confidence,
        }

        items = self._load()
        existing_ids = {entry.get("id") for entry in items if isinstance(entry, dict)}

        if candidate.id not in existing_ids:
            items.append(item)
            self._save(items)

        return {
            "ok": True,
            "queued": True,
            "candidate": item,
            "route": item["route"],
        }

    def list_candidates(
        self,
        limit: int | None = None,
        statuses: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return review candidates through a public read API.

        C1.6D-debt:
        - callers must not use private _load()
        - optional status filtering keeps synthesizer/review code simple
        - limit returns the newest N items, matching list_pending behavior
        """
        items = [
            item for item in self._load()
            if isinstance(item, dict)
        ]

        if statuses is not None:
            allowed = {str(status) for status in statuses}
            items = [
                item for item in items
                if str(item.get("status") or "") in allowed
            ]

        if limit is not None:
            if limit <= 0:
                return []
            return items[-limit:]

        return items

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return all candidates through the public queue API."""
        return self.list_candidates(limit=limit)

    def list_pending(self, limit: int = 10) -> list[dict[str, Any]]:
        items = self._load()
        pending = [
            item for item in items
            if isinstance(item, dict) and item.get("status") == "pending_review"
        ]
        return pending[-limit:]

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        """Return a candidate by id."""
        for item in self._load():
            if item.get("id") == candidate_id:
                return item
        return None

    def mark_stored(self, candidate_id: str, store_meta: dict[str, Any] | None = None) -> dict[str, Any]:
        """Mark candidate as stored after successful memory write."""
        items = self._load()
        store_meta = store_meta or {}

        for item in items:
            if item.get("id") == candidate_id:
                item["status"] = "stored"
                item["user_decision"] = "approved"
                item["stored_at"] = datetime.now().isoformat(timespec="seconds")
                item["store_meta"] = store_meta
                self._save(items)

                self.audit.log(
                    event="memory_candidate_stored",
                    query=str(item.get("query") or ""),
                    candidate_id=candidate_id,
                    action="stored",
                    payload={
                        "status": item.get("status"),
                        "tier": item.get("tier"),
                        "confidence": item.get("confidence"),
                        "source_urls": item.get("source_urls", []),
                        "store_meta": store_meta,
                    },
                )

                return {"ok": True, "candidate": item}

        return {
            "ok": False,
            "error": "candidate bulunamadi.",
            "candidate_id": candidate_id,
        }


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

                self.audit.log(
                    event="memory_candidate_decision",
                    query=str(item.get("query") or ""),
                    candidate_id=candidate_id,
                    action=decision,
                    payload={
                        "status": item.get("status"),
                        "tier": item.get("tier"),
                        "confidence": item.get("confidence"),
                        "source_urls": item.get("source_urls", []),
                    },
                )

                return {"ok": True, "candidate_id": candidate_id, "candidate": item}

        return {
            "ok": False,
            "error": "candidate bulunamadi.",
            "candidate_id": candidate_id,
        }

    def expire_old(self, now: datetime | None = None) -> dict[str, Any]:
        """Mark expired review candidates without deleting data.

        C1.3A:
        - pending_review/deferred candidates with past expires_at become expired
        - stored/rejected records are kept as audit history
        - no physical deletion in this phase
        """
        now = now or datetime.now()
        items = self._load()
        changed = 0
        expired_ids: list[str] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            status = str(item.get("status") or "")
            if status not in {"pending_review", "deferred"}:
                continue

            expires_at = item.get("expires_at")
            if not expires_at:
                continue

            try:
                expires_dt = datetime.fromisoformat(str(expires_at))
            except Exception:
                continue

            if expires_dt <= now:
                item["status"] = "expired"
                item["user_decision"] = item.get("user_decision") or "expired"
                item["decided_at"] = now.isoformat(timespec="seconds")
                changed += 1
                expired_ids.append(str(item.get("id") or ""))

                self.audit.log(
                    event="memory_candidate_expired",
                    query=str(item.get("query") or ""),
                    candidate_id=item.get("id"),
                    action="expired",
                    payload={
                        "previous_status": status,
                        "expires_at": expires_at,
                        "source_type": item.get("source_type"),
                        "memory_type": item.get("memory_type"),
                        "storage_target": item.get("storage_target"),
                        "sensitivity": item.get("sensitivity"),
                        "tags": item.get("tags", []),
                    },
                )

        if changed:
            self._save(items)

        return {
            "ok": True,
            "changed": changed,
            "expired_ids": [cid for cid in expired_ids if cid],
            "path": str(self.path),
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
            return "Araştırma sonucu boş döndü."

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
        if "Güven: high" in research_text or "Guven: high" in research_text:
            return 80
        if "Güven: medium" in research_text or "Guven: medium" in research_text:
            return 60
        if "Güven:" in research_text or "Guven:" in research_text:
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
Güven: high / 100
Güven nedeni: high_trust_domain, documentation_or_research_signal
Özet: Official documentation and current API pricing information for models."""

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
