"""C1.6G: provenance links injected into promotion metadata."""

from __future__ import annotations
from agents.memory_synthesis_promoter import MemorySynthesisPromoter


def _candidate(**overrides):
    base = {
        "id": "cand_synth_001",
        "status": "approved",
        "user_decision": "approved",
        "source_type": "synthesis",
        "proposal_type": "synthesized_memory",
        "memory_type": "semantic",
        "storage_target": "review_queue",
        "sensitivity": "normal",
        "summary": "Jarvis gelistirme aktif.",
        "theme": "jarvis",
        "source_count": 2,
        "source_ids": ["src_a", "src_b"],
        "confidence": 80,
        "route": {
            "memory_type": "semantic",
            "storage_target": "review_queue",
            "sensitivity": "normal",
            "requires_review": True,
            "allow_vector": False,
        },
    }
    base.update(overrides)
    return base


class FakeQueue:
    def __init__(self, candidate):
        self.candidate = candidate
        self.stored = []

    def get(self, candidate_id):
        if self.candidate["id"] == candidate_id:
            return self.candidate
        return None

    def mark_stored(self, candidate_id, store_meta=None):
        self.stored.append((candidate_id, store_meta or {}))
        self.candidate["status"] = "stored"
        return {"ok": True, "candidate": self.candidate}


class FakeMemory:
    def __init__(self, doc_id="vec_001"):
        self.doc_id = doc_id
        self.calls = []

    def remember(self, user_msg, jarvis_msg, meta=None):
        self.calls.append((user_msg, jarvis_msg, meta or {}))
        return self.doc_id


def test_promote_metadata_contains_source_links():
    candidate = _candidate()
    promoter = MemorySynthesisPromoter(
        queue=FakeQueue(candidate),
        memory=FakeMemory(),
    )
    result = promoter.promote(candidate["id"])

    assert result["ok"] is True
    meta = result["metadata"]
    assert "source_links" in meta
    assert isinstance(meta["source_links"], list)


def test_promote_source_links_count_matches_source_ids():
    candidate = _candidate(source_ids=["src_a", "src_b"])
    promoter = MemorySynthesisPromoter(
        queue=FakeQueue(candidate),
        memory=FakeMemory(),
    )
    result = promoter.promote(candidate["id"])
    meta = result["metadata"]
    assert len(meta["source_links"]) == 2


def test_promote_source_links_has_resolved_field():
    candidate = _candidate(source_ids=["src_a", "src_b"])
    promoter = MemorySynthesisPromoter(
        queue=FakeQueue(candidate),
        memory=FakeMemory(),
    )
    result = promoter.promote(candidate["id"])
    link = result["metadata"]["source_links"][0]
    assert "resolved" in link
    assert "id" in link


def test_promote_provenance_summary_in_metadata():
    candidate = _candidate(source_ids=["src_a", "src_b"])
    promoter = MemorySynthesisPromoter(
        queue=FakeQueue(candidate),
        memory=FakeMemory(),
    )
    result = promoter.promote(candidate["id"])
    meta = result["metadata"]
    assert "provenance_resolved" in meta
    assert "provenance_total" in meta
    assert meta["provenance_total"] == 2
