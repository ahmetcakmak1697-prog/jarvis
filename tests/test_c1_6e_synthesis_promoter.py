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

