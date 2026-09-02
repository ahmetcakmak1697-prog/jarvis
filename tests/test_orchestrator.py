"""
orchestrator helper davranış kilidi.
Saf fonksiyonlar + gerçek git mekaniği (geçici repo) ile.
"""
import json
import subprocess
import time

import pytest

import orchestrator as O


# --------------------------------------------------------------------------- #
# Saf yardımcılar
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("path,globs,expected", [
    ("jarvis/api/x.py", ["jarvis/api/**"], True),
    ("jarvis/api/x.py", ["**/api/**"], True),
    ("jarvis/x.py", ["jarvis/**"], True),
    ("jarvis\\x.py", ["jarvis/**"], True),          # Windows backslash
    ("other/x.py", ["jarvis/**"], False),
    ("jarvis", ["jarvis/**"], True),                # dizinin kendisi
    ("jarvis/sub/deep.py", ["jarvis/sub"], True),   # prefix eşleşmesi
])
def test_path_matches(path, globs, expected):
    assert O._path_matches(path, globs) is expected


@pytest.mark.parametrize("path,expected", [
    (".env", True),
    ("config/.env", True),
    ("pkg/secrets/key.txt", True),
    ("deploy/cert.pem", True),
    ("memory", True),                 # dizinin kendisi
    ("memory/store.db", True),        # altındaki
    ("jarvis/normal.py", False),
])
def test_is_forbidden(path, expected):
    forbidden = [".env", ".env.*", "**/.env", "**/secrets/**",
                 "**/*.pem", "**/id_rsa", "memory/**"]
    assert O._is_forbidden(path, forbidden) is expected


def test_strip_tests_removes_test_paths():
    paths = ["jarvis/x.py", "tests/test_x.py", "pkg/tests/test_y.py"]
    out = O._strip_tests(paths)
    assert "jarvis/x.py" in out
    assert all("test" not in p for p in out)


def test_is_judgment_true_cases():
    assert O._is_judgment({"kind": "architectural"})
    assert O._is_judgment({"kind": "spec"})
    assert O._is_judgment({"kind": "integration"})
    assert O._is_judgment({"autonomy": "human_required"})
    assert O._is_judgment({"acceptance_criteria_human": ["x"]})


def test_is_judgment_false_for_plain_implement():
    assert not O._is_judgment({"kind": "implement", "autonomy": "auto"})


def test_is_judgment_does_not_include_correctness_critical():
    # correctness_critical TEK BAŞINA yargı değil -> maker yine koşar (sonra escalation imzaya çeker).
    assert not O._is_judgment({"kind": "implement", "autonomy": "auto",
                               "correctness_critical": True})


@pytest.mark.parametrize("crit,expected", [
    (["reference test", "property invariant", "mutation gate"], True),
    (["oracle karşılaştırma", "invariant kontrol", "mutation skoru"], True),
    (["reference", "property"], False),                 # mutation eksik
    (["reference", "mutation"], False),                 # property eksik
    (["property", "mutation"], False),                  # reference eksik
    (["pytest geçti"], False),
])
def test_has_correctness_gates(crit, expected):
    assert O._has_correctness_gates({"acceptance_criteria_machine": crit}) is expected


# --------------------------------------------------------------------------- #
# Contract üretimi
# --------------------------------------------------------------------------- #

def test_gen_contract_strips_tests_for_implement():
    step = {"id": "X", "kind": "implement",
            "allowed_paths": ["jarvis/x.py", "tests/test_x.py"],
            "acceptance_criteria_machine": ["pytest"]}
    c = O._gen_contract(step)
    assert "jarvis/x.py" in c["allowed_paths"]
    assert all("test" not in p for p in c["allowed_paths"])     # spec-by-test
    assert c["human_review_required"] is False
    assert ".env" in c["forbidden_paths"]
    assert "pytest" in c["required_commands"]


def test_gen_contract_keeps_tests_for_spec():
    step = {"id": "X", "kind": "spec",
            "allowed_paths": ["tests/test_x.py"],
            "acceptance_criteria_human": ["insan kararı"]}
    c = O._gen_contract(step)
    assert "tests/test_x.py" in c["allowed_paths"]   # spec adımında testler izinli
    assert c["human_review_required"] is True


# --------------------------------------------------------------------------- #
# select_next: dosya sırası + bağımlılık
# --------------------------------------------------------------------------- #

def test_select_next_respects_file_order():
    steps = [
        {"id": "A", "status": "done"},
        {"id": "B", "status": "todo"},
        {"id": "C", "status": "todo"},
    ]
    assert O._select_next(steps)["id"] == "B"


def test_select_next_blocks_on_unmet_dependency():
    steps = [
        {"id": "A", "status": "todo"},
        {"id": "B", "status": "todo", "depends_on": ["A"]},
    ]
    # A henüz done değil -> B seçilemez, A seçilir
    assert O._select_next(steps)["id"] == "A"


def test_select_next_allows_when_dependency_done():
    steps = [
        {"id": "A", "status": "done"},
        {"id": "B", "status": "todo", "depends_on": ["A"]},
    ]
    assert O._select_next(steps)["id"] == "B"


def test_select_next_none_when_all_done():
    steps = [{"id": "A", "status": "done"}]
    assert O._select_next(steps) is None


# --------------------------------------------------------------------------- #
# Gerçek git: repo fixture
# --------------------------------------------------------------------------- #

def _run(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _run(r, "init", "-q")
    _run(r, "config", "user.email", "t@t.t")
    _run(r, "config", "user.name", "t")
    _run(r, "config", "commit.gpgsign", "false")
    pkg = r / "pkg"
    pkg.mkdir()
    (pkg / "keep.py").write_text("x = 1\n")
    _run(r, "add", "-A")
    _run(r, "commit", "-q", "-m", "init")
    return r


# --------------------------------------------------------------------------- #
# _read_verdict: katı eşleşme
# --------------------------------------------------------------------------- #

def _write_report(d, name, payload):
    (d / name).write_text(json.dumps(payload), encoding="utf-8")


def test_read_verdict_matches_correct_contract(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    _write_report(d, "verifier_report_S1.json", {"task_id": "S1", "verdict": "PASS"})
    assert O._read_verdict(d, "S1", 0.0) == "PASS"


def test_read_verdict_no_substring_crosstalk_s1_vs_s12(tmp_path):
    # S12 raporu, S1 sorgusunu KİRLETMEMELİ (dosya adı task_id içerse de task_id key farklı).
    d = tmp_path / "reports"
    d.mkdir()
    _write_report(d, "verifier_report_S1.json", {"task_id": "S1", "verdict": "PASS"})
    _write_report(d, "verifier_report_S12.json", {"task_id": "S12", "verdict": "FAIL"})
    assert O._read_verdict(d, "S1", 0.0) == "PASS"
    assert O._read_verdict(d, "S12", 0.0) == "FAIL"


def test_read_verdict_missing_dir_is_fail(tmp_path):
    assert O._read_verdict(tmp_path / "nope", "S1", 0.0) == "FAIL"


def test_read_verdict_wrong_id_is_fail(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    _write_report(d, "verifier_report_S1.json", {"task_id": "OTHER", "verdict": "PASS"})
    assert O._read_verdict(d, "S1", 0.0) == "FAIL"


def test_read_verdict_stale_report_rejected(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    f = d / "verifier_report_S1.json"
    _write_report(d, "verifier_report_S1.json", {"task_id": "S1", "verdict": "PASS"})
    import os
    old = time.time() - 3600
    os.utime(f, (old, old))
    # min_mtime = şimdi -> 1 saat önceki rapor reddedilir -> FAIL
    assert O._read_verdict(d, "S1", time.time()) == "FAIL"


def test_read_verdict_task_id_key_fallback(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    _write_report(d, "verifier_report_T1.json", {"task_id": "T1", "verdict": "PASS"})
    assert O._read_verdict(d, "T1", 0.0) == "PASS"


# --------------------------------------------------------------------------- #
# _safe_commit: izinli / yasak / kapsam-dışı / rename
# --------------------------------------------------------------------------- #

def test_safe_commit_commits_allowed(repo):
    (repo / "pkg" / "new.py").write_text("y = 2\n")
    ok, msg = O._safe_commit(repo, ["pkg/**"], [".env"], "add new")
    assert ok, msg
    assert "new.py" in _run(repo, "show", "--name-only", "--oneline", "HEAD").stdout


def test_safe_commit_refuses_forbidden(repo):
    (repo / ".env").write_text("SECRET=1\n")
    (repo / "pkg" / "new.py").write_text("y = 2\n")
    ok, msg = O._safe_commit(repo, ["pkg/**", ".env"], [".env", "**/.env"], "x")
    assert not ok
    assert ".env" in msg


def test_safe_commit_refuses_out_of_scope_source(repo):
    # İzinli alan pkg/a.py; ama pkg/b.py da değişmiş -> kısmi commit REDDEDİLİR.
    (repo / "pkg" / "a.py").write_text("a = 1\n")
    (repo / "pkg" / "b.py").write_text("b = 1\n")
    ok, msg = O._safe_commit(repo, ["pkg/a.py"], [".env"], "x")
    assert not ok
    assert "b.py" in msg


def test_safe_commit_ignores_bookkeeping_files(repo):
    # roadmap_state.json gibi defter dosyaları kapsam-dışı SAYILMAZ.
    (repo / "pkg" / "a.py").write_text("a = 1\n")
    (repo / "roadmap_state.json").write_text("{}\n")
    ok, msg = O._safe_commit(repo, ["pkg/a.py"], [".env"], "x")
    assert ok, msg


def test_safe_commit_handles_staged_rename(repo):
    # Stage'lenmiş rename porcelain'de "R old -> new" görünür; _path NEW tarafını almalı.
    _run(repo, "mv", "pkg/keep.py", "pkg/renamed.py")
    ok, msg = O._safe_commit(repo, ["pkg/**"], [".env"], "rename")
    assert ok, msg
    names = _run(repo, "show", "--name-only", "--oneline", "HEAD").stdout
    assert "renamed.py" in names


def test_safe_commit_nothing_to_stage(repo):
    ok, msg = O._safe_commit(repo, ["pkg/**"], [".env"], "noop")
    assert not ok
    assert "yok" in msg.lower() or "no" in msg.lower()
