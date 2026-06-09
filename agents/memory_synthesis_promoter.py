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

        source_ids = candidate.get("source_ids") or []
        if not isinstance(source_ids, list) or not source_ids:
            return self._blocked("missing_source_ids")

        try:
            source_count = int(candidate.get("source_count") or 0)
        except (TypeError, ValueError):
            source_count = 0

        if source_count < self.MIN_SOURCE_COUNT:
            return self._blocked("insufficient_source_count")

        route_memory_type = str(route.get("memory_type") or "").strip()
        route_storage_target = str(route.get("storage_target") or "").strip()
        route_sensitivity = str(route.get("sensitivity") or "").strip()
        route_requires_review = bool(route.get("requires_review"))
        route_allow_vector = bool(route.get("allow_vector"))

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
