"""C1.7-3A MemoryMaturityScorer tests."""
from __future__ import annotations


def _record(**overrides):
    from datetime import datetime, timedelta
    base = {
        "id": "mem_001",
        "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "last_accessed_at": None,
        "access_count": 0,
        "tier": "recall",
        "confidence": 80,
        "review_status": "approved",
        "storage_status": "stored",
    }
    base.update(overrides)
    return base


def test_returns_dict_with_required_fields():
    from agents.memory_maturity import MemoryMaturityScorer
    s = MemoryMaturityScorer()
    result = s.score(_record())
    assert "maturity_score" in result
    assert "maturity_level" in result
    assert "reason" in result
    assert "signals" in result


def test_score_range_0_to_100():
    from agents.memory_maturity import MemoryMaturityScorer
    s = MemoryMaturityScorer()
    result = s.score(_record())
    assert 0 <= result["maturity_score"] <= 100


def test_maturity_level_valid():
    from agents.memory_maturity import MemoryMaturityScorer
    s = MemoryMaturityScorer()
    result = s.score(_record())
    assert result["maturity_level"] in ("fresh", "warming", "stable", "archival")


def test_fresh_card_is_fresh():
    from agents.memory_maturity import MemoryMaturityScorer
    from datetime import datetime
    s = MemoryMaturityScorer()
    result = s.score(_record(created_at=datetime.now().isoformat(), access_count=0))
    assert result["maturity_level"] == "fresh"


def test_old_low_access_is_archival():
    from agents.memory_maturity import MemoryMaturityScorer
    from datetime import datetime, timedelta
    s = MemoryMaturityScorer()
    result = s.score(_record(
        created_at=(datetime.now() - timedelta(days=180)).isoformat(),
        access_count=0,
        tier="archival",
    ))
    assert result["maturity_level"] == "archival"


def test_core_tier_scores_higher():
    from agents.memory_maturity import MemoryMaturityScorer
    from datetime import datetime, timedelta
    s = MemoryMaturityScorer()
    core = s.score(_record(tier="core", access_count=5))
    recall = s.score(_record(tier="recall", access_count=5))
    assert core["maturity_score"] >= recall["maturity_score"]


def test_no_side_effects(tmp_path):
    from agents.memory_maturity import MemoryMaturityScorer
    import os
    before = set(os.listdir(tmp_path))
    s = MemoryMaturityScorer()
    s.score(_record())
    after = set(os.listdir(tmp_path))
    assert before == after
