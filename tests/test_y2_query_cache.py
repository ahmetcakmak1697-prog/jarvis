"""Y2-1 QueryCache exact match tests."""
from __future__ import annotations


def _cache(tmp_path):
    from agents.query_cache import QueryCache
    return QueryCache(data_root=tmp_path)


def test_miss_returns_none(tmp_path):
    c = _cache(tmp_path)
    assert c.get_exact("bilinmeyen soru xyz") is None


def test_put_and_get_exact(tmp_path):
    c = _cache(tmp_path)
    c.put("RTX 3070 kac watt?", "220W TDP.", source_route="knowledge_card")
    result = c.get_exact("RTX 3070 kac watt?")
    assert result is not None
    assert result["answer"] == "220W TDP."


def test_normalize_ignores_case(tmp_path):
    c = _cache(tmp_path)
    c.put("RTX 3070 Kac Watt?", "220W TDP.", source_route="knowledge_card")
    result = c.get_exact("rtx 3070 kac watt?")
    assert result is not None


def test_normalize_strips_whitespace(tmp_path):
    c = _cache(tmp_path)
    c.put("  RTX 3070 kac watt?  ", "220W.", source_route="kc")
    result = c.get_exact("RTX 3070 kac watt?")
    assert result is not None


def test_hit_count_increments(tmp_path):
    c = _cache(tmp_path)
    c.put("Soru?", "Cevap.", source_route="kc")
    c.get_exact("Soru?")
    c.get_exact("Soru?")
    result = c.get_exact("Soru?")
    assert result["hit_count"] >= 2


def test_different_questions_dont_collide(tmp_path):
    c = _cache(tmp_path)
    c.put("soru bir", "cevap bir", source_route="kc")
    c.put("soru iki", "cevap iki", source_route="kc")
    assert c.get_exact("soru bir")["answer"] == "cevap bir"
    assert c.get_exact("soru iki")["answer"] == "cevap iki"


def test_persists_across_instances(tmp_path):
    from agents.query_cache import QueryCache
    c1 = QueryCache(data_root=tmp_path)
    c1.put("kalici soru?", "kalici cevap.", source_route="kc")
    c2 = QueryCache(data_root=tmp_path)
    result = c2.get_exact("kalici soru?")
    assert result is not None
    assert result["answer"] == "kalici cevap."


def test_stats_returns_count(tmp_path):
    c = _cache(tmp_path)
    c.put("s1", "c1", source_route="kc")
    c.put("s2", "c2", source_route="kc")
    stats = c.stats()
    assert stats["total_entries"] == 2
