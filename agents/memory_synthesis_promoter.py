"""C1.6E-3 synthesis promotion gate.

This module validates whether an approved synthesized memory candidate may be
promoted from review_queue into a controlled semantic memory write path.

C1.6E-3A intentionally does not write to VectorMemory, does not mutate the
queue, and does not bypass MemoryCandidateWriter route guards.
"""

from __future__ import annotations

from typing import Any


class MemorySynthesisPromoter:
    """Validate synthesis candidates before any semantic promotion.

    The existing MemoryCandidateWriter review_queue guard must remain strict.
    This promoter is a separate gate for a later controlled promotion path.
    """

    MIN_SOURCE_COUNT = 2

    def __init__(self, queue: Any | None = None, memory: Any | None = None, root: Any | None = None) -> None:
        self.queue = queue
        self.memory = memory
        self.root = root

    def _get_queue(self) -> Any:
        if self.queue is not None:
            return self.queue

        from agents.memory_candidate_queue import MemoryCandidateQueue

        self.queue = MemoryCandidateQueue(self.root) if self.root is not None else MemoryCandidateQueue()
        return self.queue

    def _get_memory(self) -> Any:
        if self.memory is not None:
            return self.memory

        from tools.vector_memory import VectorMemory

        self.memory = VectorMemory()
        return self.memory

    def _blocked(self, reason: str) -> dict[str, Any]:
        return {
            "ok": True,
            "promotable": False,
            "reason": reason,
        }

    def _accepted(self) -> dict[str, Any]:
        return {
            "ok": True,
            "promotable": True,
            "reason": "promotable",
        }

    def validate_candidate(self, candidate: dict[str, Any] | None) -> dict[str, Any]:
        """Return whether a candidate is safe to promote.

        This is a pure validation step:
        - no VectorMemory write
        - no queue mutation
        - no mark_stored call
        - no route guard bypass
        """
        if not isinstance(candidate, dict):
            return self._blocked("invalid_candidate")

        candidate_id = str(candidate.get("id") or "").strip()
        status = str(candidate.get("status") or "").strip()
        user_decision = str(candidate.get("user_decision") or "").strip()
        proposal_type = str(candidate.get("proposal_type") or "").strip()
        source_type = str(candidate.get("source_type") or "").strip()
        memory_type = str(candidate.get("memory_type") or "").strip()
        storage_target = str(candidate.get("storage_target") or "").strip()
        sensitivity = str(candidate.get("sensitivity") or "").strip()
        summary = str(candidate.get("summary") or "").strip()
        theme = str(candidate.get("theme") or "").strip()
        route = candidate.get("route") or {}

        if not candidate_id:
            return self._blocked("missing_candidate_id")

        if status == "stored":
            return self._blocked("already_stored")

        if status != "approved":
            return self._blocked("candidate_not_approved")

        if user_decision != "approved":
            return self._blocked("candidate_not_user_approved")

        if proposal_type != "synthesized_memory":
            return self._blocked("invalid_proposal_type")

        if source_type != "synthesis":
            return self._blocked("invalid_source_type")

        if sensitivity != "normal":
            return self._blocked("unsafe_sensitivity")

        if not summary:
            return self._blocked("missing_summary")

        if not theme:
            return self._blocked("missing_theme")

        source_ids_raw = candidate.get("source_ids") or []
        if not isinstance(source_ids_raw, list):
            return self._blocked("missing_source_ids")

        source_ids = [str(source_id).strip() for source_id in source_ids_raw if str(source_id).strip()]
        if not source_ids:
            return self._blocked("missing_source_ids")

        try:
            source_count = int(candidate.get("source_count") or 0)
        except (TypeError, ValueError):
            source_count = 0

        if source_count < self.MIN_SOURCE_COUNT:
            return self._blocked("insufficient_source_count")

        if len(source_ids) < self.MIN_SOURCE_COUNT:
            return self._blocked("insufficient_source_ids")

        if not isinstance(route, dict):
            return self._blocked("invalid_review_route")

        route_memory_type = str(route.get("memory_type") or "").strip()
        route_storage_target = str(route.get("storage_target") or "").strip()
        route_sensitivity = str(route.get("sensitivity") or "").strip()
        route_requires_review = route.get("requires_review")
        route_allow_vector = route.get("allow_vector")

        valid_review_route = (
            memory_type == "semantic"
            and storage_target == "review_queue"
            and route_memory_type == "semantic"
            and route_storage_target == "review_queue"
            and route_sensitivity == "normal"
            and route_requires_review is True
            and route_allow_vector is False
        )

        if not valid_review_route:
            return self._blocked("invalid_review_route")

        return self._accepted()

    def build_promotion_metadata(self, candidate: dict[str, Any] | None) -> dict[str, Any]:
        """Build safe semantic-write metadata for a promotable synthesis candidate.

        This method is intentionally side-effect free:
        - no VectorMemory write
        - no queue mutation
        - no candidate route mutation
        - no mark_stored call

        The returned metadata is for a later controlled promoter write path, not
        a way to modify the candidate's original review_queue route.
        """
        validation = self.validate_candidate(candidate)
        if not validation.get("promotable"):
            return {
                "ok": True,
                "built": False,
                "reason": validation.get("reason", "not_promotable"),
            }

        assert isinstance(candidate, dict)  # validate_candidate already checked this.

        route = candidate.get("route") or {}
        if not isinstance(route, dict):
            return {
                "ok": True,
                "built": False,
                "reason": "invalid_review_route",
            }

        source_ids = [
            str(source_id).strip()
            for source_id in list(candidate.get("source_ids") or [])
            if str(source_id).strip()
        ]
        tags = [str(tag).strip() for tag in list(route.get("tags") or []) if str(tag).strip()]

        try:
            source_count = int(candidate.get("source_count") or 0)
        except (TypeError, ValueError):
            source_count = 0

        try:
            confidence = int(candidate.get("confidence") or route.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0

        from datetime import datetime

        from agents.memory_provenance import MemoryProvenanceResolver
        resolver = MemoryProvenanceResolver()
        provenance = resolver.summarize(source_ids)

        metadata = {
            "source": "memory_synthesis_promoter",
            "source_type": "synthesis",
            "candidate_id": str(candidate.get("id") or ""),
            "schema_version": "c1.6e3",
            "promotion_schema_version": "c1.6e3",
            "memory_type": "semantic",
            "storage_target": "vector",
            "sensitivity": "normal",
            "proposal_type": "synthesized_memory",
            "theme": str(candidate.get("theme") or "").strip(),
            "source_count": source_count,
            "source_ids": source_ids,
            "confidence": confidence,
            "promoted_by": "MemorySynthesisPromoter",
            "allow_vector": True,
            "requires_review": False,
            "original_route_storage_target": str(route.get("storage_target") or ""),
            "original_route_requires_review": bool(route.get("requires_review")),
            "original_route_allow_vector": bool(route.get("allow_vector")),
            "tags": tags,
            "promoted_at": datetime.now().isoformat(timespec="seconds"),
            "source_links": provenance["links"],
            "provenance_resolved": provenance["resolved"],
            "provenance_unresolved": provenance["unresolved"],
            "provenance_total": provenance["total"],
        }

        return {
            "ok": True,
            "built": True,
            "reason": "metadata_built",
            "metadata": metadata,
        }


    def promote(self, candidate_id: str) -> dict[str, Any]:
        """Promote an approved synthesis candidate into vector memory.

        Safety rules:
        - validate_candidate must pass first
        - original review_queue route is not modified
        - mark_stored is called only after successful VectorMemory.remember
        """
        candidate_id = str(candidate_id or "").strip()
        queue = self._get_queue()

        candidate = queue.get(candidate_id)
        if not candidate:
            return {
                "ok": False,
                "promoted": False,
                "reason": "candidate_not_found",
                "candidate_id": candidate_id,
            }

        metadata_result = self.build_promotion_metadata(candidate)
        if not metadata_result.get("built"):
            return {
                "ok": False,
                "promoted": False,
                "reason": metadata_result.get("reason", "not_promotable"),
                "candidate_id": candidate_id,
            }

        metadata = metadata_result["metadata"]
        summary = str(candidate.get("summary") or "").strip()
        theme = str(candidate.get("theme") or "synthesis").strip() or "synthesis"

        memory = self._get_memory()
        vector_doc_id = memory.remember(f"memory_synthesis:{theme}", summary, metadata)

        if not vector_doc_id:
            return {
                "ok": False,
                "promoted": False,
                "reason": "vector_write_failed",
                "candidate_id": candidate_id,
            }

        store_meta = {
            "vector_doc_id": vector_doc_id,
            "promoted_by": metadata["promoted_by"],
            "promotion_schema_version": metadata["promotion_schema_version"],
            "source_ids": list(metadata.get("source_ids") or []),
            "source_count": metadata.get("source_count"),
            "theme": metadata.get("theme"),
            "confidence": metadata.get("confidence"),
            "promoted_at": metadata.get("promoted_at"),
        }

        stored = queue.mark_stored(candidate_id, store_meta)

        if not stored.get("ok"):
            return {
                "ok": False,
                "promoted": False,
                "reason": "queue_mark_stored_failed",
                "candidate_id": candidate_id,
                "vector_doc_id": vector_doc_id,
                "queue": stored,
            }

        return {
            "ok": True,
            "promoted": True,
            "reason": "promoted",
            "candidate_id": candidate_id,
            "vector_doc_id": vector_doc_id,
            "metadata": metadata,
            "queue": stored,
        }

