"""Y2-2 QueryCache semantic match tests.

Spec:
- threshold=0.80, min_common_tokens=3
- Short query (<3 tokens): require perfect overlap (score=1.0)
- Negation mismatch: iyi != iyi degil -> always miss
- Digit-aware: RTX 3070 != RTX 4090
"""
from __future__ import annotations


def _cache(tmp_path):
    from agents.query_cache import QueryCache
    return QueryCache(data_root=tmp_path)


def test_semantic_miss_returns_none_when_empty(tmp_path):
    c = _cache(tmp_path)
    assert c.get_semantic("RTX 3070 kac watt?") is None


def test_semantic_hit_natural_word_order_variant(tmp_path):
    """Gemini: gercek hayat senaryosu, Yoda-dizilimi degil."""
    c = _cache(tmp_path)
    c.put("RTX 3070 ekran karti kac watt tuketiyor?", "220W TDP.", source_route="kc")
    result = c.get_semantic("RTX 3070 ekran karti kac watt?")
    assert result is not None
    assert result["answer"] == "220W TDP."
    assert result["match_type"] == "semantic"
    assert "similarity" in result
    assert "matched_question" in result


def test_hardware_model_number_prevents_wrong_hit(tmp_path):
    """Gemini kritik test: 3070 != 4090, digit-aware tokenizer."""
    c = _cache(tmp_path)
    c.put("RTX 3070 kac watt?", "220W.", source_route="kc")
    result = c.get_semantic("RTX 4090 kac watt?")
    assert result is None


def test_negation_mismatch_always_miss(tmp_path):
    """iyi mi? != iyi degil mi? -> kesinlikle miss."""
    c = _cache(tmp_path)
    c.put("RTX 3070 ekran karti iyi mi?", "Evet, iyi.", source_route="kc")
    result = c.get_semantic("RTX 3070 ekran karti iyi degil mi?")
    assert result is None


def test_min_common_tokens_blocks_partial_match(tmp_path):
    """Ollama model sil vs guncelle: 2 ortak token, min=3 -> miss."""
    c = _cache(tmp_path)
    c.put("Ollama model sil", "Silindi.", source_route="kc")
    result = c.get_semantic("Ollama model guncelle", min_common_tokens=3)
    assert result is None


def test_short_query_perfect_overlap_hits(tmp_path):
    """GPU sicaklik (2 token): birebir ayni -> hit."""
    c = _cache(tmp_path)
    c.put("GPU sicaklik", "70 derece.", source_route="kc")
    result = c.get_semantic("GPU sicaklik")
    assert result is not None
    assert result["answer"] == "70 derece."


def test_short_query_one_token_diff_miss(tmp_path):
    """GPU voltaj vs GPU sicaklik: kisa sorgu, farkli token -> miss."""
    c = _cache(tmp_path)
    c.put("GPU sicaklik", "70 derece.", source_route="kc")
    result = c.get_semantic("GPU voltaj")
    assert result is None


def test_exact_takes_priority_over_semantic(tmp_path):
    """Exact cache varsa semantic cagrilmamali (router seviyesinde)."""
    c = _cache(tmp_path)
    c.put("RTX 3070 kac watt?", "Exact cevap.", source_route="kc")
    exact = c.get_exact("RTX 3070 kac watt?")
    assert exact is not None
    assert exact["answer"] == "Exact cevap."
