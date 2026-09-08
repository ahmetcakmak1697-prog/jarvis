"""B09: exercise real tool boundaries with synthetic files and fake transports."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def surface(tmp_path, monkeypatch):
    from tools import tools

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(tools, "PROJECT_PATH", root)
    return tools, root


@pytest.mark.parametrize("method", ["read_file", "write_file", "analyze_file"])
@pytest.mark.parametrize("absolute", [True, False])
def test_outside_paths_are_denied(surface, monkeypatch, method, absolute):
    tools, root = surface
    outside = root.parent / "outside.txt"
    outside.write_text("SYNTHETIC_OUTSIDE", encoding="utf-8")
    monkeypatch.setattr(tools.Confirm, "ask", lambda *a, **k: True)
    target = str(outside) if absolute else "../outside.txt"
    args = [target, "changed"] if method == "write_file" else [target]
    result = getattr(tools, method)(*args)
    assert outside.read_text(encoding="utf-8") == "SYNTHETIC_OUTSIDE"
    assert "SYNTHETIC_OUTSIDE" not in result
    assert "Hata" in result or "engell" in result.lower()


@pytest.mark.parametrize("target", [".env", "nested/.env.local", ".git/config",
                                    "credentials.json", "id_rsa", "key.pem",
                                    "file.txt:private", "C:relative.txt"])
def test_sensitive_or_ambiguous_paths_never_reach_file_io(surface, monkeypatch, target):
    tools, root = surface
    reads = []
    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "read_text", lambda path, **kw: reads.append(str(path)) or "SYNTHETIC")
        tools.read_file(target)
    assert reads == []


def test_write_requires_human_confirmation_even_with_auto_commands(surface, monkeypatch):
    tools, root = surface
    target = root / "note.txt"
    target.write_text("original", encoding="utf-8")
    monkeypatch.setattr(tools, "AUTO_RUN_COMMANDS", True, raising=False)
    monkeypatch.setattr(tools.Confirm, "ask", lambda *a, **k: False)
    tools.write_file("note.txt", "replacement")
    assert target.read_text(encoding="utf-8") == "original"


def test_approved_write_and_normal_read_still_work(surface, monkeypatch):
    tools, root = surface
    monkeypatch.setattr(tools.Confirm, "ask", lambda *a, **k: True)
    tools.write_file("folder/note.txt", "approved content")
    assert tools.read_file("folder/note.txt") == "approved content"


def test_directory_link_cannot_escape_project(surface, monkeypatch):
    tools, root = surface
    outside = root.parent / "outside-dir"
    outside.mkdir()
    (outside / "note.txt").write_text("SYNTHETIC_JUNCTION", encoding="utf-8")
    link = root / "link"
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        monkeypatch.setattr(tools.Confirm, "ask", lambda *a, **k: True)
        assert "SYNTHETIC_JUNCTION" not in tools.read_file("link/note.txt")
        tools.write_file("link/note.txt", "changed")
        assert (outside / "note.txt").read_text(encoding="utf-8") == "SYNTHETIC_JUNCTION"
    finally:
        if os.name == "nt":
            os.rmdir(link)  # Remove only the synthetic junction, never its target.
        else:
            link.unlink()


def test_git_diff_treats_shell_separators_as_one_literal_path(surface, monkeypatch):
    tools, root = surface
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        output = "note.txt & echo AUDIT_MARKER\0" if "--name-only" in args else "synthetic diff"
        return SimpleNamespace(stdout=output, stderr="", returncode=0)
    monkeypatch.setattr(tools.subprocess, "run", run)
    path = "note.txt & echo AUDIT_MARKER"
    (root / path).write_text("synthetic file", encoding="utf-8")
    tools.git_diff(path)
    assert len(calls) == 2
    assert "--name-only" in calls[0][0]
    args, kwargs = calls[1]
    assert isinstance(args, list)
    assert kwargs.get("shell") is False
    assert args[-2:] == ["--", path]
    assert "--no-ext-diff" in args and "--no-textconv" in args


def test_search_treats_query_as_text_without_a_shell(surface, monkeypatch):
    tools, root = surface
    query = 'needle"; echo AUDIT_MARKER'
    (root / "note.txt").write_text(query, encoding="utf-8")
    calls = []
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **kw: calls.append(a) or SimpleNamespace(stdout="", stderr="", returncode=0))
    result = tools.search_in_files(query, "*.txt")
    assert calls == []
    assert "note.txt:1:" in result


def test_generic_runner_never_uses_shell(surface, monkeypatch):
    tools, root = surface
    calls = []
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **kw: calls.append(kw) or SimpleNamespace(stdout="", stderr="", returncode=0))
    tools._run(["git", "status", "--short"], cwd=root)
    assert calls[0]["shell"] is False


def test_terminal_requires_explicit_human_approval(surface, monkeypatch):
    tools, root = surface
    monkeypatch.setattr(tools, "AUTO_RUN_COMMANDS", True, raising=False)
    monkeypatch.setattr(tools.Confirm, "ask", lambda *a, **kw: False)
    calls = []
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **kw: calls.append(a) or SimpleNamespace(stdout="", stderr="", returncode=0))
    tools.run_terminal_command("echo synthetic")
    assert calls == []


@pytest.mark.parametrize("method", ["fetch_webpage", "deep_research"])
def test_tls_certificate_failures_do_not_fetch_unverified_content(surface, monkeypatch, method):
    import requests
    tools, root = surface
    verify_settings = []
    def get(url, **kwargs):
        verify_settings.append(kwargs.get("verify", True))
        if kwargs.get("verify", True):
            raise requests.exceptions.SSLError("SYNTHETIC_CERT_FAILURE")
        response = requests.Response()
        response.status_code = 200
        response._content = b"<p>SYNTHETIC_UNVERIFIED_CONTENT_LONG_ENOUGH</p>"
        return response
    monkeypatch.setattr(requests, "get", get)
    class Search:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def text(self, *args, **kwargs):
            return [{"href": "https://synthetic.invalid", "title": "Synthetic", "body": "search snippet"}]
    monkeypatch.setitem(sys.modules, "duckduckgo_search", SimpleNamespace(DDGS=Search))
    result = getattr(tools, method)("https://synthetic.invalid")
    assert verify_settings and all(verify_settings)
    assert "SYNTHETIC_UNVERIFIED_CONTENT" not in result


def test_python_execution_is_unavailable_through_all_public_entries(surface):
    tools, root = surface
    assert "run_python_code" not in tools.TOOL_REGISTRY
    assert not any(item["name"] == "run_python_code" for item in tools.TOOL_DEFINITIONS)
    assert "42" not in tools.run_python_code("print(40+2)")


@pytest.mark.parametrize("argument", [".", "nested"])
def test_git_diff_rejects_directory_arguments_before_git(surface, monkeypatch, argument):
    tools, root = surface
    (root / "nested").mkdir()
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout="SYNTHETIC_DIRECTORY_DIFF", stderr="", returncode=0)
    monkeypatch.setattr(tools.subprocess, "run", run)
    result = tools.git_diff(argument)
    assert calls == [], "directory pathspec bypassed per-file filtering"
    assert "SYNTHETIC_DIRECTORY_DIFF" not in result


@pytest.mark.parametrize("argument", ["deleted-dir", "deleted-dir/child"])
def test_git_diff_rejects_missing_paths_before_git(surface, monkeypatch, argument):
    tools, root = surface
    calls = []
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **kw: calls.append(a) or SimpleNamespace(stdout="SYNTHETIC_DIRECTORY_DIFF", stderr="", returncode=0))
    tools.git_diff(argument)
    assert calls == [], "missing path could still be a Git directory pathspec"



def test_git_diff_does_not_expand_index_directory_prefix(surface, monkeypatch):
    tools, root = surface
    (root / "nested").write_text("now a regular file", encoding="utf-8")
    content_calls = []
    def run(args, **kwargs):
        if "--name-only" in args:
            return SimpleNamespace(stdout="nested/credentials.json\0", stderr="", returncode=0)
        content_calls.append(args)
        return SimpleNamespace(stdout="SYNTHETIC_INDEX_CHILD_CONTENT", stderr="", returncode=0)
    monkeypatch.setattr(tools.subprocess, "run", run)
    result = tools.git_diff("nested")
    assert content_calls == [], "worktree file expanded to an index directory"
    assert "SYNTHETIC_INDEX_CHILD_CONTENT" not in result
