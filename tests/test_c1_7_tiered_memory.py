"""C1.7 Tiered Memory tests."""
from __future__ import annotations


def test_memory_tier_values():
    from agents.tiered_memory import MemoryTier
    assert MemoryTier.CORE == "core"
    assert MemoryTier.RECALL == "recall"
    assert MemoryTier.ARCHIVAL == "archival"
    assert MemoryTier.EPISODIC == "episodic"


def test_tiered_router_returns_core_for_identity():
    from agents.tiered_memory import TieredMemoryRouter
    r = TieredMemoryRouter()
    tier = r.classify("Benim adim Ahmet, Jarvis projesi yapiyorum.")
    assert tier == "core"


def test_tiered_router_returns_episodic_for_session():
    from agents.tiered_memory import TieredMemoryRouter
    r = TieredMemoryRouter()
    tier = r.classify("Bugun C1.7 patch yaziyoruz.")
    assert tier == "episodic"


def test_tiered_router_returns_recall_for_frequent():
    from agents.tiered_memory import TieredMemoryRouter
    r = TieredMemoryRouter()
    tier = r.classify("RTX 3070 8GB VRAM kullaniyorum, Qwen3 8B calistiriyorum.")
    assert tier == "recall"


def test_tiered_router_returns_archival_for_old():
    from agents.tiered_memory import TieredMemoryRouter
    r = TieredMemoryRouter()
    tier = r.classify("2019 yilinda Python ogrendim.")
    assert tier == "archival"


def test_classify_returns_string():
    from agents.tiered_memory import TieredMemoryRouter
    r = TieredMemoryRouter()
    result = r.classify("herhangi bir metin")
    assert isinstance(result, str)
    assert result in ("core", "recall", "archival", "episodic")


def test_tier_metadata_contains_tier():
    from agents.tiered_memory import TieredMemoryRouter
    r = TieredMemoryRouter()
    meta = r.classify_with_meta("Jarvis projesi aktif.")
    assert "tier" in meta
    assert "tier_reason" in meta
    assert meta["tier"] in ("core", "recall", "archival", "episodic")
