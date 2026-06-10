"""C1.7: MemoryRoute tier field tests."""
from __future__ import annotations


def test_memory_route_has_tier_field():
    from agents.memory_schema import MemorySchemaMapper
    mapper = MemorySchemaMapper()
    route = mapper.route_exchange("Benim adim Ahmet, Jarvis yapiyorum.")
    d = route.to_dict()
    assert "tier" in d
    assert "tier_reason" in d


def test_tier_core_for_identity_text():
    from agents.memory_schema import MemorySchemaMapper
    mapper = MemorySchemaMapper()
    route = mapper.route_exchange("Benim adim Ahmet.")
    assert route.tier == "core"


def test_tier_episodic_for_session_text():
    from agents.memory_schema import MemorySchemaMapper
    mapper = MemorySchemaMapper()
    route = mapper.route_exchange("Bugun commit attik.")
    assert route.tier == "episodic"


def test_tier_is_string():
    from agents.memory_schema import MemorySchemaMapper
    mapper = MemorySchemaMapper()
    route = mapper.route_exchange("Herhangi bir metin.")
    assert isinstance(route.tier, str)
    assert route.tier in ("core", "recall", "archival", "episodic")
