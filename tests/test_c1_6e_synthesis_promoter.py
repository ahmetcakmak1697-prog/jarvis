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
