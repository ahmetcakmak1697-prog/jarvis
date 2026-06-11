"""Z - System Chaos & Fuzz Testing (Property-Based).

hypothesis ile sistemin hic crash etmemesini garanti ederiz.
Normal testlerin gozemeyecegi edge-case'leri yakalar.

Run: python -m pytest tests/test_z_chaos_fuzzer.py -q
"""
from __future__ import annotations
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st


class _FakeLedger:
    def check_and_consume(self, *a, **kw):
        return {"allowed": True, "reason": "within_limit"}

class _FakeVM:
    def find_similar(self, *a, **kw):
        return []


# ----------------------------------------------------------------
# 1. Tokenizer + Jaccard invariant
# Sistemin tokenizer ve Jaccard hesabi hic crash etmemeli,
# skor her zaman 0.0-1.0 araliginda olmali.
# ----------------------------------------------------------------
@given(query=st.text(), card_text=st.text())
@settings(max_examples=300, deadline=None)
def test_fuzz_tokenizer_jaccard_never_crashes(query, card_text):
    from agents.knowledge_card_retriever import _tokens, _jaccard
    q_tok = _tokens(query)
    c_tok = _tokens(card_text)
    score = _jaccard(q_tok, c_tok)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


# ----------------------------------------------------------------
# 2. Router resilience
# Router'a 0-5000 karakter arasi rastgele metin gondersek bile
# hic crash etmemeli, gecerli bir decision donemli.
# ----------------------------------------------------------------
@given(chaos=st.text(min_size=0, max_size=5000))
@settings(max_examples=200, deadline=None)
def test_fuzz_router_never_crashes(chaos):
    from agents.local_first_router import LocalFirstRouter
    router = LocalFirstRouter(cost_ledger=_FakeLedger(), vector_memory=_FakeVM())
    try:
        result = router.route(chaos)
    except Exception as e:
        pytest.fail(f"Router coktu: {type(e).__name__}: {e} | girdi: {repr(chaos[:80])}")
    assert "decision" in result
    assert result["decision"] in (
        "answer_local", "ask_external", "clarify",
        "no_answer", "redacted_blocked", "external_blocked"
    )
    assert "route" in result
    assert "confidence" in result


# ----------------------------------------------------------------
# 3. Redaction bypass attempt
# API key, etrafina ne kadar rastgele metin sarsak da
# redacted_blocked olmali.
# ----------------------------------------------------------------
@given(prefix=st.text(max_size=100), suffix=st.text(max_size=100))
@settings(max_examples=150, deadline=None)
def test_fuzz_api_key_always_blocked(prefix, suffix):
    from agents.local_first_router import LocalFirstRouter
    malicious = f"{prefix} OPENAI_API_KEY=sk-abc123defghijklmnopqrstuvwxyz {suffix}"
    router = LocalFirstRouter(cost_ledger=_FakeLedger(), vector_memory=_FakeVM())
    result = router.route(malicious)
    assert result["decision"] == "redacted_blocked", (
        f"API key kacti! decision={result['decision']} | girdi: {repr(malicious[:120])}"
    )


# ----------------------------------------------------------------
# 4. QueryCache semantic never crashes
# Cache'e rastgele soru sorulunca hic crash etmemeli.
# ----------------------------------------------------------------
@given(query=st.text(min_size=0, max_size=1000))
@settings(max_examples=200, deadline=None)
def test_fuzz_query_cache_semantic_never_crashes(query):
    import tempfile
    from agents.query_cache import QueryCache
    with tempfile.TemporaryDirectory() as td:
        cache = QueryCache(data_root=Path(td))
        cache.put("RTX 3070 kac watt?", "220W.", source_route="fuzz")
        try:
            result = cache.get_semantic(query)
            assert result is None or isinstance(result.get("answer"), str)
        except Exception as e:
            pytest.fail(f"QueryCache coktu: {type(e).__name__}: {e} | girdi: {repr(query[:80])}")


# ----------------------------------------------------------------
# 5. EpisodicBuffer never crashes on arbitrary input
# ----------------------------------------------------------------
@given(
    event_type=st.text(max_size=50),
    summary=st.text(max_size=500),
)
@settings(max_examples=150, deadline=None)
def test_fuzz_episodic_buffer_never_crashes(event_type, summary):
    import tempfile
    from agents.episodic_buffer import EpisodicBuffer
    with tempfile.TemporaryDirectory() as td:
        buf = EpisodicBuffer(root=Path(td))
        try:
            result = buf.append_event(event_type, summary)
            assert "ok" in result
        except Exception as e:
            pytest.fail(f"EpisodicBuffer coktu: {type(e).__name__}: {e}")
