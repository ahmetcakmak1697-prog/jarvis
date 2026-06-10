"""Y1 ModelCascade tests.

L0 = local_memory  / free      (KnowledgeCard + VectorMemory)
L1 = local_small   / free      (kucuk yerel model)
L2 = local_main    / cheap     (ana yerel model)
L3 = research      / moderate  (guclu yerel/kontroll?)
L4 = external      / expensive (premium API, son care)
"""
from __future__ import annotations


def test_cascade_returns_required_fields():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("Jarvis nedir?")
    assert "level" in result
    assert "model" in result
    assert "reason" in result
    assert "cost_tier" in result


def test_cascade_level_values_valid():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("test sorusu")
    assert result["level"] in ("L0", "L1", "L2", "L3", "L4")


def test_cost_tier_values_valid():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("test sorusu")
    assert result["cost_tier"] in ("free", "cheap", "moderate", "expensive")


def test_simple_greeting_is_L1():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("merhaba")
    assert result["level"] in ("L0", "L1")
    assert result["cost_tier"] == "free"


def test_deep_research_is_L3():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("derinlemesine analiz et ve detayli rapor hazirla")
    assert result["level"] == "L3"
    assert result["cost_tier"] == "moderate"


def test_L4_only_via_force():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    normal = c.select("karmasik soru ama force yok")
    assert normal["level"] != "L4"
    forced = c.select("test", force_level="L4")
    assert forced["level"] == "L4"
    assert forced["cost_tier"] == "expensive"


def test_L0_model_is_local_memory():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("test", force_level="L0")
    assert result["level"] == "L0"
    assert result["model"] == "local_memory"
    assert result["cost_tier"] == "free"


def test_no_side_effects():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    r1 = c.select("soru bir")
    r2 = c.select("soru iki")
    assert r1["level"] is not None
    assert r2["level"] is not None
