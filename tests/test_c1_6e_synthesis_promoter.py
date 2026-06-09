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
        "summary": "Jarvis gelistirme calismalari aktif ve surekli ilerliyor.",
        "theme": "jarvis",
        "source_count": 3,
        "source_ids": ["cand_a", "cand_b", "cand_c"],
        "confidence": 80,
        "route": {
            "schema_version": "c1.6d",
            "memory_type": "semantic",
            "storage_target": "review_queue",
            "sensitivity": "normal",
            "requires_review": True,
            "allow_vector": False,
            "allow_daily_summary": True,
            "tags": ["synthesis", "theme:jarvis"],
            "confidence": 80,
        },
    }
    base.update(overrides)
    return base


def test_validate_rejects_non_approved_candidate():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(status="pending_review", user_decision=None))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "candidate_not_approved"


def test_validate_rejects_non_approved_user_decision():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(status="approved", user_decision="deferred"))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "candidate_not_user_approved"


def test_validate_rejects_already_stored_candidate():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(status="stored", user_decision="approved"))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "already_stored"


def test_validate_rejects_wrong_proposal_type():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(proposal_type="conversation_memory"))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_proposal_type"


def test_validate_rejects_wrong_source_type():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(source_type="conversation"))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_source_type"


def test_validate_rejects_unsafe_sensitivity():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(sensitivity="sensitive"))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "unsafe_sensitivity"


def test_validate_rejects_missing_source_ids():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(source_ids=[]))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "missing_source_ids"


def test_validate_rejects_insufficient_source_count():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(source_count=1, source_ids=["cand_a"]))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "insufficient_source_count"


def test_validate_rejects_missing_summary():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(summary=""))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "missing_summary"


def test_validate_rejects_missing_theme():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(theme=""))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "missing_theme"


def test_validate_rejects_wrong_route_shape():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(
        _candidate(
            storage_target="vector",
            route={
                "schema_version": "c1.6d",
                "memory_type": "semantic",
                "storage_target": "vector",
                "sensitivity": "normal",
                "requires_review": False,
                "allow_vector": True,
            },
        )
    )

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_review_route"


def test_validate_accepts_safe_approved_synthesis_candidate():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate())

    assert result["ok"] is True
    assert result["promotable"] is True
    assert result["reason"] == "promotable"


def test_build_promotion_metadata_requires_promotable_candidate():
    promoter = MemorySynthesisPromoter()

    result = promoter.build_promotion_metadata(
        _candidate(status="pending_review", user_decision=None)
    )

    assert result["ok"] is True
    assert result["built"] is False
    assert result["reason"] == "candidate_not_approved"


def test_build_promotion_metadata_does_not_mutate_candidate_route():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()
    original_route = dict(candidate["route"])
    original_storage_target = candidate["storage_target"]

    result = promoter.build_promotion_metadata(candidate)

    assert result["ok"] is True
    assert result["built"] is True
    assert candidate["route"] == original_route
    assert candidate["storage_target"] == original_storage_target
    assert candidate["route"]["storage_target"] == "review_queue"
    assert candidate["route"]["requires_review"] is True
    assert candidate["route"]["allow_vector"] is False


def test_build_promotion_metadata_contains_required_provenance_fields():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()

    result = promoter.build_promotion_metadata(candidate)

    assert result["ok"] is True
    assert result["built"] is True

    meta = result["metadata"]
    assert meta["source"] == "memory_synthesis_promoter"
    assert meta["source_type"] == "synthesis"
    assert meta["candidate_id"] == "cand_synth_001"
    assert meta["schema_version"] == "c1.6e3"
    assert meta["promotion_schema_version"] == "c1.6e3"
    assert meta["memory_type"] == "semantic"
    assert meta["storage_target"] == "vector"
    assert meta["sensitivity"] == "normal"
    assert meta["proposal_type"] == "synthesized_memory"
    assert meta["theme"] == "jarvis"
    assert meta["source_count"] == 3
    assert meta["source_ids"] == ["cand_a", "cand_b", "cand_c"]
    assert meta["confidence"] == 80
    assert meta["promoted_by"] == "MemorySynthesisPromoter"
    assert meta["allow_vector"] is True
    assert meta["requires_review"] is False
    assert meta["original_route_storage_target"] == "review_queue"
    assert meta["original_route_requires_review"] is True
    assert meta["original_route_allow_vector"] is False
    assert isinstance(meta["promoted_at"], str)
    assert len(meta["promoted_at"]) >= 19


def test_build_promotion_metadata_copies_source_ids_not_aliases():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()

    result = promoter.build_promotion_metadata(candidate)
    meta = result["metadata"]

    candidate["source_ids"].append("late_mutation")

    assert meta["source_ids"] == ["cand_a", "cand_b", "cand_c"]


def test_build_promotion_metadata_preserves_tags_from_route():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()

    result = promoter.build_promotion_metadata(candidate)

    meta = result["metadata"]
    assert meta["tags"] == ["synthesis", "theme:jarvis"]


def test_validate_rejects_missing_candidate_id():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(id=""))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "missing_candidate_id"


def test_validate_rejects_non_dict_route():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(route="not-a-dict"))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_review_route"


def test_validate_rejects_missing_route_requires_review():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()
    candidate["route"] = dict(candidate["route"])
    candidate["route"].pop("requires_review")

    result = promoter.validate_candidate(candidate)

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_review_route"


def test_validate_rejects_string_route_requires_review():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()
    candidate["route"] = dict(candidate["route"])
    candidate["route"]["requires_review"] = "true"

    result = promoter.validate_candidate(candidate)

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_review_route"


def test_validate_rejects_missing_route_allow_vector():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()
    candidate["route"] = dict(candidate["route"])
    candidate["route"].pop("allow_vector")

    result = promoter.validate_candidate(candidate)

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_review_route"


def test_validate_rejects_string_route_allow_vector():
    promoter = MemorySynthesisPromoter()
    candidate = _candidate()
    candidate["route"] = dict(candidate["route"])
    candidate["route"]["allow_vector"] = "false"

    result = promoter.validate_candidate(candidate)

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "invalid_review_route"


def test_validate_rejects_blank_source_ids():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(source_ids=["", "   "], source_count=2))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "missing_source_ids"


def test_validate_rejects_source_ids_count_below_min_even_if_source_count_claims_more():
    promoter = MemorySynthesisPromoter()

    result = promoter.validate_candidate(_candidate(source_ids=["cand_a"], source_count=3))

    assert result["ok"] is True
    assert result["promotable"] is False
    assert result["reason"] == "insufficient_source_ids"


def test_build_promotion_metadata_requires_candidate_id():
    promoter = MemorySynthesisPromoter()

    result = promoter.build_promotion_metadata(_candidate(id=""))

    assert result["ok"] is True
    assert result["built"] is False
    assert result["reason"] == "missing_candidate_id"


class FakePromotionQueue:
    def __init__(self, candidate=None):
        self.candidate = candidate
        self.mark_stored_calls = []

    def get(self, candidate_id):
        if self.candidate and self.candidate.get("id") == candidate_id:
            return self.candidate
        return None

    def mark_stored(self, candidate_id, store_meta=None):
        self.mark_stored_calls.append((candidate_id, store_meta or {}))
        if self.candidate and self.candidate.get("id") == candidate_id:
            self.candidate["status"] = "stored"
            self.candidate["store_meta"] = store_meta or {}
            return {"ok": True, "candidate": self.candidate}
        return {"ok": False, "error": "candidate bulunamadi.", "candidate_id": candidate_id}


class FakePromotionMemory:
    def __init__(self, doc_id="vec_001"):
        self.doc_id = doc_id
        self.calls = []

    def remember(self, user_msg, jarvis_msg, meta=None):
        self.calls.append((user_msg, jarvis_msg, meta or {}))
        return self.doc_id


def test_promote_rejects_missing_candidate():
    queue = FakePromotionQueue(candidate=None)
    memory = FakePromotionMemory()
    promoter = MemorySynthesisPromoter(queue=queue, memory=memory)

    result = promoter.promote("missing_id")

    assert result["ok"] is False
    assert result["promoted"] is False
    assert result["reason"] == "candidate_not_found"
    assert memory.calls == []
    assert queue.mark_stored_calls == []


def test_promote_rejects_non_promotable_candidate_without_memory_write():
    candidate = _candidate(status="pending_review", user_decision=None)
    queue = FakePromotionQueue(candidate=candidate)
    memory = FakePromotionMemory()
    promoter = MemorySynthesisPromoter(queue=queue, memory=memory)

    result = promoter.promote(candidate["id"])

    assert result["ok"] is False
    assert result["promoted"] is False
    assert result["reason"] == "candidate_not_approved"
    assert memory.calls == []
    assert queue.mark_stored_calls == []


def test_promote_does_not_mark_stored_when_memory_write_fails():
    candidate = _candidate()
    queue = FakePromotionQueue(candidate=candidate)
    memory = FakePromotionMemory(doc_id="")
    promoter = MemorySynthesisPromoter(queue=queue, memory=memory)

    result = promoter.promote(candidate["id"])

    assert result["ok"] is False
    assert result["promoted"] is False
    assert result["reason"] == "vector_write_failed"
    assert len(memory.calls) == 1
    assert queue.mark_stored_calls == []
    assert candidate["status"] == "approved"


def test_promote_marks_stored_after_successful_memory_write():
    candidate = _candidate()
    queue = FakePromotionQueue(candidate=candidate)
    memory = FakePromotionMemory(doc_id="vec_synth_001")
    promoter = MemorySynthesisPromoter(queue=queue, memory=memory)

    result = promoter.promote(candidate["id"])

    assert result["ok"] is True
    assert result["promoted"] is True
    assert result["reason"] == "promoted"
    assert result["vector_doc_id"] == "vec_synth_001"
    assert len(memory.calls) == 1
    assert len(queue.mark_stored_calls) == 1

    stored_candidate_id, store_meta = queue.mark_stored_calls[0]
    assert stored_candidate_id == candidate["id"]
    assert store_meta["vector_doc_id"] == "vec_synth_001"
    assert store_meta["promoted_by"] == "MemorySynthesisPromoter"
    assert store_meta["promotion_schema_version"] == "c1.6e3"
    assert store_meta["source_ids"] == ["cand_a", "cand_b", "cand_c"]
    assert candidate["status"] == "stored"


def test_promote_does_not_mutate_candidate_route():
    candidate = _candidate()
    original_route = dict(candidate["route"])
    queue = FakePromotionQueue(candidate=candidate)
    memory = FakePromotionMemory(doc_id="vec_synth_001")
    promoter = MemorySynthesisPromoter(queue=queue, memory=memory)

    result = promoter.promote(candidate["id"])

    assert result["ok"] is True
    assert candidate["route"] == original_route
    assert candidate["route"]["storage_target"] == "review_queue"
    assert candidate["route"]["requires_review"] is True
    assert candidate["route"]["allow_vector"] is False

