"""
Tests for j0_live_status.py — live, injectable, Unicode-safe.

All tests use fake git output and fake roadmap JSON.
No dependency on real repo state or real git.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from j0_live_status import LiveStatus, collect_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_git_runner(lines: List[str], clean: bool = True):
    """Return a GitRunner that returns fixed output."""
    porcelain = "" if clean else " M scripts/j0_live_status.py\n"

    def _run(args: List[str]) -> str:
        if args[0] == "log":
            return "\n".join(lines) + "\n"
        if args[0] == "status":
            return porcelain
        raise ValueError(f"unexpected git args: {args}")

    return _run


def _fake_roadmap_loader(data: Dict[str, Any]):
    def _load() -> Any:
        return data
    return _load


_FAKE_GIT_LOG = [
    "abc1234 Son commit mesaji",
    "def5678 Onceki commit",
    "ghi9012 Daha onceki commit",
    "jkl3454 Eski commit",
    "mno6789 Cok eski commit",
    "pqr0123 En eski commit",
]


# ---- 1: parse fake git log and include current HEAD ----


def test_parses_fake_git_log_and_includes_head():
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": []})

    status = collect_status(git_runner, roadmap_loader)

    assert status.head_commit_hash == "abc1234"
    assert status.head_commit_title == "Son commit mesaji"
    assert len(status.recent_commits) == 5


# ---- 2: FAZ-3-E1 status remains in_progress when roadmap says so ----


def test_faz3e1_status_in_progress_from_roadmap():
    steps: List[dict] = [
        {"id": "FAZ-3-E1", "title": "Proaktif davranis", "status": "in_progress"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})

    status = collect_status(git_runner, roadmap_loader)

    assert status.faz3e1 is not None
    assert status.faz3e1["status"] == "in_progress"


# ---- 3: runtime delivery not claimed when FAZ-3-E1 is in_progress ----


def test_runtime_delivery_not_claimed_when_faz3e1_in_progress():
    steps: List[dict] = [
        {"id": "FAZ-3-E1", "title": "Proaktif davranis", "status": "in_progress"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})

    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "Runtime delivery / Telegram g\u00f6nderme / scheduler" in summary
    assert "hen\u00fcz devrede de\u011fil" in summary


# ---- 4: dirty/clean status ----


def test_dirty_clean_status():
    for clean in (True, False):
        git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=clean)
        roadmap_loader = _fake_roadmap_loader({"steps": []})
        status = collect_status(git_runner, roadmap_loader)
        assert status.working_tree_clean == clean


# ---- 5: no RAG/static snapshot required ----


def test_no_static_snapshot():
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": []})
    status = collect_status(git_runner, roadmap_loader)
    # The method never reads a static file; all data is injected.
    # This test verifies the function returns without error.
    assert status.head_commit_hash == "abc1234"


# ---- 6: Turkish-ready output asserts real Unicode labels ----


def test_turkish_unicode_labels_in_summary():
    steps: list = [
        {"id": "FAZ-TEST", "title": "Test", "status": "in_progress"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "\u015eu an devam eden" in summary
    assert "\u00c7al\u0131\u015fma a\u011fac\u0131" in summary
    assert "TEM\u0130Z" in summary


# ---- 7: reject ASCII-degraded labels ----


def test_rejects_ascii_degraded_labels():
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": []})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    ascii_degraded = ["Calisma", "agaci", "Su an", "Sira", "TEMIZ", "KIRLI"]
    for bad in ascii_degraded:
        assert bad not in summary, f"ASCII-degraded '{bad}' found in output"


# ---- 8: reject mojibake artifacts ----


def test_rejects_mojibake_artifacts():
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": []})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    mojibake = ["\u00e2", "\u00c3", "\u00c4", "\u00c5"]
    for bad in mojibake:
        assert bad not in summary, f"Mojibake '{repr(bad)}' found in output"


# ---- 9: codepoint-level test ----


def test_codepoint_level_turkish():
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    steps: List[dict] = [
        {"id": "FAZ-3-E1", "title": "Proaktif", "status": "in_progress"},
    ]
    roadmap_loader = _fake_roadmap_loader({"steps": steps})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "\u00c7" in summary, "codepoint \u00c7 U+00C7 missing"
    assert "\u0131" in summary, "codepoint \u0131 U+0131 missing"
    assert "\u011f" in summary, "codepoint \u011f U+011F missing"
    assert "\u015e" in summary, "codepoint \u015e U+015E missing"
    assert "\u0130" in summary, "codepoint \u0130 U+0130 missing (via TEM\u0130Z or K\u0130RL\u0130)"


# ---- 10: different in_progress step reflected, not hardcoded ----


def test_different_roadmap_step_reflected():
    steps: List[dict] = [
        {"id": "FAZ-X99", "title": "Ozel test adimi", "status": "in_progress"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "FAZ-X99" in summary
    assert "Ozel test adimi" in summary


# ---- 11: changing injected git output changes tool output ----


def test_changing_git_output_changes_tool_output():
    git_runner_a = _fake_git_runner(["aaaaaa First state"], clean=True)
    git_runner_b = _fake_git_runner(["bbbbbb Second state"], clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": []})

    status_a = collect_status(git_runner_a, roadmap_loader)
    status_b = collect_status(git_runner_b, roadmap_loader)

    assert status_a.head_commit_hash == "aaaaaa"
    assert status_b.head_commit_hash == "bbbbbb"
    assert status_a.head_commit_hash != status_b.head_commit_hash
    assert "First state" in status_a.text_summary()
    assert "Second state" in status_b.text_summary()


# ---- 12: no hardcoded current focus ----


def test_no_hardcoded_current_focus():
    # When roadmap is empty, no in_progress or todo should appear.
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": []})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "\u015eu an devam eden:" not in summary
    assert "S\u0131ra bekleyen:" not in summary


# ---- 13: missing roadmap file does not crash ----


def test_missing_roadmap_no_crash():
    def failing_roadmap_loader() -> Any:
        raise FileNotFoundError("roadmap_state.json not found")

    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    status = collect_status(git_runner, failing_roadmap_loader)
    summary = status.text_summary()

    assert "HEAD:" in summary
    # Should not crash; no FAZ-3-E1 note should appear
    assert "FAZ-3-E1" not in summary


# ---- 14: in_progress and todo both display ----


def test_in_progress_and_todo_both_display():
    steps: List[dict] = [
        {"id": "FAZ-A", "title": "A adimi", "status": "in_progress"},
        {"id": "FAZ-B", "title": "B adimi", "status": "todo"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "\u015eu an devam eden:" in summary
    assert "S\u0131ra bekleyen:" in summary
    assert "FAZ-A" in summary
    assert "FAZ-B" in summary


# ---- 15: FAZ-3-E1 absent => no parked note ----


def test_no_faz3e1_parked_note_when_absent():
    steps: List[dict] = [
        {"id": "FAZ-A", "title": "Some step", "status": "in_progress"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "FAZ-3-E1" not in summary
    assert "park edilmi\u015f" not in summary
    assert "ProactivePolicy" not in summary
    assert "Runtime delivery" not in summary


# ---- 16: FAZ-3-E1 done => no in_progress/parked wording ----


def test_faz3e1_done_no_in_progress_wording():
    steps: List[dict] = [
        {"id": "FAZ-3-E1", "title": "Proaktif davranis", "status": "done"},
    ]
    git_runner = _fake_git_runner(_FAKE_GIT_LOG, clean=True)
    roadmap_loader = _fake_roadmap_loader({"steps": steps})
    status = collect_status(git_runner, roadmap_loader)
    summary = status.text_summary()

    assert "park edilmi\u015f" not in summary
    assert "FAZ-3-E1 durumu: in_progress" not in summary


# ---- 17: subprocess CLI UTF-8 encoding regression ----
def test_cli_utf8_subprocess():
    import subprocess
    import sys
    import os
    spath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "j0_live_status.py")
    # Use PYTHONIOENCODING=utf-8 to protect pipe capture.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, spath],
        capture_output=True,
        text=False,  # bytes
        env=env,
    )
    raw = result.stdout
    # Decode with strict UTF-8 — must not raise.
    text = raw.decode("utf-8")
    # Assert Turkish Unicode strings present
    assert "Çalışma ağacı" in text
    assert "Şu an" in text
    assert "Sıra" in text
    assert ("TEMİZ" in text) or ("KİRLİ" in text)
    # Assert no mojibake or ASCII degradation
    for bad in ["\ufffd", "Calisma", "Su an", "Sira", "TEMIZ", "KIRLI", "\u00e2", "\u00c3", "\u00c4", "\u00c5"]:
        assert bad not in text, f"mojibake/ascii-degraded '{bad}' found in CLI output"
