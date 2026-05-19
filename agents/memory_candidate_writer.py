"""Memory Candidate Writer - D1.9.

Stores approved memory candidates into vector memory safely.

Rules:
- only approved candidates may be stored
- MemoryPolicy must allow vector write
- sensitive/review candidates are not stored automatically
- candidate is marked as stored only after successful vector memory write
"""

from __future__ import annotations

import json

from datetime import datetime
from pathlib import Path
from typing import Any

from agents.memory_candidate_queue import MemoryCandidateQueue
from agents.memory_policy import MemoryPolicy
from agents.audit_logger import AuditLogger

try:
    from tools.vector_memory import VectorMemory
    VM_OK = True
except Exception:
    VM_OK = False


ROOT = Path(__file__).resolve().parents[1]


class MemoryCandidateWriter:
    """Approve-to-vector-memory bridge."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.queue = MemoryCandidateQueue(self.root)
        self.policy = MemoryPolicy()
        self.audit = AuditLogger(self.root)
        self.memory = VectorMemory() if VM_OK else None

    def _log_store_blocked(
        self,
        candidate_id: str,
        candidate: dict[str, Any] | None,
        reason: str,
        policy: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.audit.log(
                event="memory_candidate_store_blocked",
                query=str((candidate or {}).get("query") or ""),
                candidate_id=candidate_id,
                action="blocked",
                payload={
                    "reason": reason,
                    "status": (candidate or {}).get("status"),
                    "tier": (candidate or {}).get("tier"),
                    "confidence": (candidate or {}).get("confidence"),
                    "policy": policy or {},
                },
            )
        except Exception:
            pass


    def approve_and_store(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.queue.get(candidate_id)

        if not candidate:
            self._log_store_blocked(candidate_id, None, "candidate bulunamadi.")
            return {
                "ok": False,
                "stored": False,
                "error": "candidate bulunamadi.",
                "candidate_id": candidate_id,
            }

        status = candidate.get("status")
        if status not in {"pending_review", "approved", "deferred"}:
            self._log_store_blocked(candidate_id, candidate, f"candidate status store icin uygun degil: {status}")
            return {
                "ok": False,
                "stored": False,
                "error": f"candidate status store icin uygun degil: {status}",
                "candidate_id": candidate_id,
            }

        if not self.memory:
            self._log_store_blocked(candidate_id, candidate, "VectorMemory kullanilamiyor.")
            return {
                "ok": False,
                "stored": False,
                "error": "VectorMemory kullanilamiyor.",
                "candidate_id": candidate_id,
            }

        query = str(candidate.get("query") or "").strip()
        summary = str(candidate.get("summary") or "").strip()

        if not summary:
            self._log_store_blocked(candidate_id, candidate, "candidate summary bos.")
            return {
                "ok": False,
                "stored": False,
                "error": "candidate summary bos.",
                "candidate_id": candidate_id,
            }

        # Explicit approval means we ask policy as an explicit-save memory.
        policy_text = f"Bunu hat?rla: {summary}"
        decision = self.policy.decide(policy_text).to_dict()

        if decision.get("requires_review") is True:
            self.queue.decide(candidate_id, "approved")
            self._log_store_blocked(candidate_id, candidate, "MemoryPolicy inceleme istedi; otomatik yazilmadi.", decision)
            return {
                "ok": False,
                "stored": False,
                "error": "MemoryPolicy inceleme istedi; otomatik yazilmadi.",
                "candidate_id": candidate_id,
                "policy": decision,
            }

        if decision.get("allow_vector") is not True or decision.get("action") != "keep_long_term":
            self.queue.decide(candidate_id, "approved")
            self._log_store_blocked(candidate_id, candidate, "MemoryPolicy vector yazimina izin vermedi.", decision)
            return {
                "ok": False,
                "stored": False,
                "error": "MemoryPolicy vector yazimina izin vermedi.",
                "candidate_id": candidate_id,
                "policy": decision,
            }

        mem_meta = {
            "type": "web_memory_candidate",
            "source": "memory_candidate_queue",
            "candidate_id": candidate_id,
            "memory_action": decision.get("action", "keep_long_term"),
            "memory_importance": int(decision.get("importance", 8) or 8),
            "memory_tags": ",".join(decision.get("tags", []) or ["web_research"]),
            "allow_vector": True,
            "allow_daily_summary": bool(decision.get("allow_daily_summary", True)),
            "requires_review": False,
            "source_urls": candidate.get("source_urls", []),
            "source_scores_json": json.dumps(candidate.get("source_scores", []), ensure_ascii=False),
            "confidence": candidate.get("confidence"),
            "tier": candidate.get("tier"),
            "stored_at": datetime.now().isoformat(timespec="seconds"),
        }

        # Keep user/query and answer/summary separated for vector recall.
        self.memory.remember(query or "web_research_candidate", summary, mem_meta)

        stored = self.queue.mark_stored(candidate_id, {
            "memory_action": mem_meta["memory_action"],
            "memory_importance": mem_meta["memory_importance"],
            "memory_tags": mem_meta["memory_tags"],
            "stored_at": mem_meta["stored_at"],
        })

        return {
            "ok": True,
            "stored": True,
            "candidate_id": candidate_id,
            "status": "stored",
            "policy": decision,
            "queue": stored,
        }


if __name__ == "__main__":
    import json

    writer = MemoryCandidateWriter()
    pending = writer.queue.list_pending(limit=1)

    if not pending:
        print(json.dumps({"ok": False, "error": "pending candidate yok"}, ensure_ascii=False, indent=2))
    else:
        cid = pending[-1]["id"]
        print(json.dumps(writer.approve_and_store(cid), ensure_ascii=False, indent=2))
