from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.checkpoint_summary import (
    _base_commit,
    _commits,
    _diff_capped,
    _diffstat_capped,
    _git,
    _head,
    _load_marker,
    _root_commit,
    _safe_print,
    build,
)


def test_git_encoding_fix_never_none(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout=None, stderr=None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    cp = _git(Path("."), "rev-parse", "HEAD")
    assert cp.stdout == ""
    assert cp.stderr == ""


def test_git_encoding_fix_non_ascii(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*a, **kw):
        assert kw.get("encoding") == "utf-8"
        assert kw.get("errors") == "replace"
        return subprocess.CompletedProcess([], 0, stdout="\u015f \u0131 \u011f", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    cp = _git(Path("."), "dummy")
    assert cp.stdout == "\u015f \u0131 \u011f"


def test_commits_handles_none_stdout(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout=None, stderr=None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _commits(Path("."), "")
    assert result == []


def test_diff_capped_handles_none_stdout(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout=None, stderr=None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _diff_capped(Path("."), "")
    assert result == "(diff yok)"


def test_diff_capped_short_diff(monkeypatch: pytest.MonkeyPatch):
    diff_text = "--- a/foo\n+++ b/foo\n@@ -1 +1 @@\n-old\n+new"
    def fake_run(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout=diff_text, stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _diff_capped(Path("."), "")
    assert "old" in result
    assert "new" in result


def test_safe_print_ascii_ok(capsys: pytest.CaptureFixture[str]):
    _safe_print("hello world")
    captured = capsys.readouterr()
    assert captured.out.rstrip() == "hello world"


def test_diffstat_capped_empty(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _diffstat_capped(Path("."), "", max_lines=5)
    assert "(de\u011fi\u015fiklik yok)" in result


def test_diffstat_capped_truncated(monkeypatch: pytest.MonkeyPatch):
    lines = "\n".join(f"{i}.py | 1 +" for i in range(20))
    def fake_run(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout=lines, stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _diffstat_capped(Path("."), "", max_lines=5)
    assert "kesildi" in result
    assert result.count("\n") <= 7


def test_base_commit_no_marker(monkeypatch: pytest.MonkeyPatch):
    head_sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    def fake_head(*a, **kw):
        return subprocess.CompletedProcess([], 0, stdout=head_sha, stderr="")
    monkeypatch.setattr(subprocess, "run", fake_head)
    result = _base_commit(Path("."), {}, full_history=False)
    assert result == head_sha


def test_base_commit_no_marker_full_history(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*a, **kw):
        args = a[0] if a else []
        if "rev-list" in args and "--max-parents=0" in args:
            return subprocess.CompletedProcess([], 0, stdout="root123", stderr="")
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _base_commit(Path("."), {}, full_history=True)
    assert result == "root123"


def test_base_commit_uses_marker():
    marker = {"commit": "abcdef123456"}
    result = _base_commit(Path("."), marker, full_history=False)
    assert result == "abcdef123456"


def _fake_git_run(*a, **kw) -> subprocess.CompletedProcess:
    args = a[0] if a else []
    if "rev-parse" in args and "HEAD" in args:
        return subprocess.CompletedProcess([], 0, stdout="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", stderr="")
    if "rev-list" in args and "--max-parents=0" in args:
        return subprocess.CompletedProcess([], 0, stdout="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", stderr="")
    if "rev-list" in args and "--count" in args:
        return subprocess.CompletedProcess([], 0, stdout="0", stderr="")
    if "log" in args:
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    if "diff" in args:
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    return subprocess.CompletedProcess([], 0, stdout="", stderr="")


def test_build_no_marker_no_full_history_small(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    state_file = tmp_path / "state.json"
    state_file.write_text('{"steps": []}', encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr(subprocess, "run", _fake_git_run)
    result = build(repo=tmp_path, state_path=state_file, reports_dir=reports, ledger=None)
    assert "aaaaaaaa" in result
    assert len(result) < 5000


def test_build_no_marker_full_history_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    state_file = tmp_path / "state.json"
    state_file.write_text('{"steps": []}', encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr(subprocess, "run", _fake_git_run)
    result = build(repo=tmp_path, state_path=state_file, reports_dir=reports, ledger=None, full_history=True)
    assert "bbbbbbbb" in result


def test_build_report_char_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    state_file = tmp_path / "state.json"
    state_file.write_text('{"steps": []}', encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr(subprocess, "run", _fake_git_run)
    result = build(repo=tmp_path, state_path=state_file, reports_dir=reports, ledger=None, max_report_chars=100)
    assert "k\u0131salt\u0131ld\u0131" in result
    assert len(result) <= 250


def test_safe_print_unicode_fallback(monkeypatch: pytest.MonkeyPatch):
    written: list[str] = []
    class FakeStdout:
        encoding = "ascii"
        def reconfigure(self, **kw):
            pass
        def write(self, s: str):
            if any(ord(c) > 127 for c in s):
                raise UnicodeEncodeError("ascii", s, 0, 1, "nope")
            written.append(s)
        def flush(self):
            pass
    monkeypatch.setattr("sys.stdout", FakeStdout())
    _safe_print("\u015f \u0131 \u011f emoji \U0001f600")
    assert len(written) > 0
    assert all(ord(c) < 128 for part in written for c in part.rstrip("\r\n"))
