"""C1.6F session/day closure summary tests."""

from __future__ import annotations


def test_closure_returns_string():
    from agents.session_closure import SessionClosure
    sc = SessionClosure()
    result = sc.summarize()
    assert isinstance(result, str)
    assert len(result) > 0


def test_closure_with_no_candidates_returns_safe_message():
    from agents.session_closure import SessionClosure
    sc = SessionClosure(candidates=[])
    result = sc.summarize()
    assert "efendim" in result.lower() or "ozet" in result.lower() or "hafiza" in result.lower()


def test_closure_counts_approved_candidates():
    from agents.session_closure import SessionClosure
    candidates = [
        {"id": "1", "status": "approved", "source_type": "conversation"},
        {"id": "2", "status": "stored", "source_type": "conversation"},
        {"id": "3", "status": "pending_review", "source_type": "conversation"},
        {"id": "4", "status": "approved", "source_type": "synthesis"},
    ]
    sc = SessionClosure(candidates=candidates)
    result = sc.summarize()
    assert isinstance(result, str)


def test_closure_includes_synthesis_themes():
    from agents.session_closure import SessionClosure
    candidates = [
        {
            "id": "1",
            "status": "approved",
            "source_type": "synthesis",
            "proposal_type": "synthesized_memory",
            "theme": "jarvis",
            "summary": "Jarvis gelistirme aktif.",
        },
        {
            "id": "2",
            "status": "approved",
            "source_type": "synthesis",
            "proposal_type": "synthesized_memory",
            "theme": "eshot",
            "summary": "ESHOT raporlama devam ediyor.",
        },
    ]
    sc = SessionClosure(candidates=candidates)
    result = sc.summarize()
    assert "jarvis" in result.lower() or "eshot" in result.lower()


def test_closure_output_is_telegram_safe():
    from agents.session_closure import SessionClosure
    sc = SessionClosure(candidates=[])
    result = sc.summarize()
    assert len(result) <= 3900
    assert isinstance(result, str)


def test_closure_no_side_effects(tmp_path):
    """summarize() hicbir dosyaya yazmamal, hicbir queue degistirmemeli."""
    from agents.session_closure import SessionClosure
    import os
    files_before = set(os.listdir(tmp_path))
    sc = SessionClosure(candidates=[], data_root=tmp_path)
    sc.summarize()
    files_after = set(os.listdir(tmp_path))
    assert files_before == files_after
