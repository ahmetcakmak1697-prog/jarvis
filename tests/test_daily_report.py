"""
daily_report saf rapor mantigi (git'siz).
"""
from daily_report import _blocked, _eligible_next, _needs_signature


def test_eligible_next_filters_unmet_deps():
    steps = [
        {"id": "A", "status": "done"},
        {"id": "B", "status": "todo", "depends_on": ["A"]},
        {"id": "C", "status": "todo", "depends_on": ["B"]},
    ]
    ids = [s["id"] for s in _eligible_next(steps)]
    assert ids == ["B"]


def test_blocked_lists_missing_deps():
    steps = [
        {"id": "A", "status": "todo"},
        {"id": "C", "status": "todo", "depends_on": ["A", "X"]},
    ]
    blocked = _blocked(steps)
    by_id = {s["id"]: missing for s, missing in blocked}
    assert "C" in by_id
    assert set(by_id["C"]) == {"A", "X"}


def test_needs_signature_includes_needs_human_with_reason():
    steps = [{"id": "S", "title": "t", "status": "needs_human",
              "evidence": {"reason": "dogruluk-kritik", "review_branch": "review/S"}}]
    sig = _needs_signature(steps, [])
    assert any("S" in x and "dogruluk-kritik" in x and "review/S" in x for x in sig)


def test_needs_signature_includes_in_progress_judgment():
    steps = [{"id": "E1", "title": "proaktif", "status": "in_progress",
              "kind": "architectural", "autonomy": "human_required"}]
    sig = _needs_signature(steps, [])
    assert any("E1" in x for x in sig)


def test_needs_signature_includes_failed_verifier():
    verdicts = [{"task": "T9", "verdict": "FAIL", "file": "r.json"}]
    sig = _needs_signature([], verdicts)
    assert any("T9" in x and "FAIL" in x for x in sig)


def test_needs_signature_skips_clean_in_progress_auto():
    steps = [{"id": "M", "title": "mech", "status": "in_progress",
              "kind": "implement", "autonomy": "auto"}]
    assert _needs_signature(steps, []) == []
