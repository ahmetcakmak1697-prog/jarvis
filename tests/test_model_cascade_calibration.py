"""ModelCascade calibration regression tests."""
from __future__ import annotations


def test_python_how_to_goes_l2_not_l3():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("Python listede tekrar eden elemanlari nasil buluruz?")
    assert result["level"] == "L2", f"Beklenen L2, geldi {result['level']}"


def test_django_how_to_goes_l2():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("Django REST framework nasil kurulur?")
    assert result["level"] == "L2", f"Beklenen L2, geldi {result['level']}"


def test_greeting_goes_l1():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("merhaba")
    assert result["level"] == "L1"


def test_deep_analysis_goes_l3():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("derinlemesine analiz et ve kapsamli rapor hazirla")
    assert result["level"] == "L3"


def test_architecture_comparison_goes_l3():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    result = c.select("RTX 3070 ile Qwen3 8B mimarisini karsilastir")
    assert result["level"] == "L3"


def test_l4_only_via_force():
    from agents.model_cascade import ModelCascade
    c = ModelCascade()
    normal = c.select("karmasik bir soru ama force yok")
    assert normal["level"] != "L4"
    forced = c.select("test", force_level="L4")
    assert forced["level"] == "L4"
