"""Tests for verifier_runner.py — deterministic automation gate."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.verifier_runner import (
    _SECRET_PATTERNS,
    _check_paths,
    _is_verifier_report,
    _load_contract,
    _make_report,
    _path_is_allowed,
    _path_is_forbidden,
    _scan_for_secrets,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ANCHOR = Path("/repo_root")


@pytest.fixture
def minimal_contract(tmp_path: Path) -> Path:
    data = {
        "task_id": "test-001",
        "goal": "test goal",
        "allowed_paths": ["scripts/", "tests/"],
        "forbidden_paths": [".env", "memory/"],
        "required_commands": [],
        "human_review_required": False,
    }
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# _load_contract
# ---------------------------------------------------------------------------


def test_missing_contract_exits(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(SystemExit) as exc:
        _load_contract(missing)
    assert exc.value.code == 2


def test_invalid_json_exits(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _load_contract(bad)
    assert exc.value.code == 2


def test_missing_key_exits(tmp_path: Path) -> None:
    p = tmp_path / "no_goal.json"
    p.write_text(json.dumps({"task_id": "x"}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _load_contract(p)
    assert exc.value.code == 2


def test_load_contract_ok(minimal_contract: Path) -> None:
    data = _load_contract(minimal_contract)
    assert data["task_id"] == "test-001"


# ---------------------------------------------------------------------------
# _make_report — human_review_required
# ---------------------------------------------------------------------------


def test_human_review_required_returns_needs_human() -> None:
    contract: dict[str, Any] = {
        "task_id": "h-001",
        "goal": "human check",
        "human_review_required": True,
    }
    report = _make_report(contract, [], [], [])
    assert report["verdict"] == "NEEDS_HUMAN"
    assert report["exit_code"] == 2


def test_missing_contract_failsafe_exit_code() -> None:
    contract: dict[str, Any] = {
        "task_id": "missing",
        "goal": "simulates missing contract fields",
        "human_review_required": False,
    }
    report = _make_report(contract, [], [], [])
    assert report["verdict"] == "PASS"
    assert report["exit_code"] == 0


# ---------------------------------------------------------------------------
# _check_paths / _path_is_allowed — scripts_bad false match
# ---------------------------------------------------------------------------


def test_scripts_bad_does_not_match_scripts() -> None:
    allowed = [_ANCHOR / "scripts"]
    assert _path_is_allowed(_ANCHOR / "scripts" / "foo.py", allowed)
    assert _path_is_allowed(_ANCHOR / "scripts", allowed)
    assert not _path_is_allowed(_ANCHOR / "scripts_bad" / "foo.py", allowed)
    assert not _path_is_allowed(_ANCHOR / "scripts_bad", allowed)


def test_forbidden_subdirectory_rejected() -> None:
    forbidden = [_ANCHOR / "memory"]
    assert _path_is_forbidden(_ANCHOR / "memory" / "secret.txt", forbidden)
    assert _path_is_forbidden(_ANCHOR / "memory", forbidden)
    assert not _path_is_forbidden(_ANCHOR / "memory_else" / "ok.txt", forbidden)


def test_check_paths_allowed_and_forbidden(tmp_path: Path) -> None:
    from scripts.verifier_runner import ROOT

    allowed = ["scripts/"]
    forbidden = [".env"]
    changed = [
        ROOT / "scripts" / "good.py",
        ROOT / ".env",
        ROOT / "scripts_bad" / "evil.py",
    ]
    errors = _check_paths(changed, allowed, forbidden)
    assert any("outside allowed_paths" in e for e in errors), (
        "scripts_bad should be flagged as outside allowed"
    )
    assert any("forbidden_paths" in e and ".env" in e for e in errors), (
        ".env should be flagged as forbidden"
    )
    assert not any("good.py" in e for e in errors), "scripts/good.py should pass"


# ---------------------------------------------------------------------------
# _scan_for_secrets
# ---------------------------------------------------------------------------


def test_labeled_secret_detected(tmp_path: Path) -> None:
    f = tmp_path / "cfg.py"
    f.write_text('api_key = "supersecretvalue12345"', encoding="utf-8")
    leaks = _scan_for_secrets([f])
    assert len(leaks) == 1
    assert "api_key" in leaks[0] or "api" in leaks[0] or "secret" in leaks[0]


def test_generic_long_string_not_detected(tmp_path: Path) -> None:
    f = tmp_path / "normal.txt"
    f.write_text("A" * 50, encoding="utf-8")
    leaks = _scan_for_secrets([f])
    assert len(leaks) == 0, "plain long alnum string without label should not fire"


def test_sk_token_detected(tmp_path: Path) -> None:
    f = tmp_path / "keys.txt"
    f.write_text("sk-" + "x" * 30, encoding="utf-8")
    leaks = _scan_for_secrets([f])
    assert len(leaks) >= 1


def test_private_key_block_detected(tmp_path: Path) -> None:
    f = tmp_path / "id_rsa"
    f.write_text("-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----", encoding="utf-8")
    leaks = _scan_for_secrets([f])
    assert len(leaks) >= 1


# ---------------------------------------------------------------------------
# _scan_for_secrets — regression: no base64/alnum 40+ broad pattern
# ---------------------------------------------------------------------------


def test_no_broad_base64_pattern_remaining() -> None:
    pat_strings = [p.pattern for p in _SECRET_PATTERNS]
    broad = [s for s in pat_strings if "A-Za-z0-9+/" in s and "40" in s]
    assert len(broad) == 0, "broad base64 40+ pattern should have been removed"


# ---------------------------------------------------------------------------
# _scan_for_secrets — human review scenarios
# ---------------------------------------------------------------------------


def test_secret_leads_to_fail_verdict() -> None:
    contract: dict[str, Any] = {"task_id": "s-001", "goal": "x", "human_review_required": False}
    report = _make_report(contract, [], ["cfg.py:1 matches secret"], [])
    assert report["verdict"] == "FAIL"
    assert report["exit_code"] == 1


def test_path_error_leads_to_fail_verdict() -> None:
    contract: dict[str, Any] = {"task_id": "p-001", "goal": "x", "human_review_required": False}
    report = _make_report(contract, [".env is forbidden"], [], [])
    assert report["verdict"] == "FAIL"
    assert report["exit_code"] == 1


# ---------------------------------------------------------------------------
# _is_verifier_report — ignore generated reports
# ---------------------------------------------------------------------------


def test_verifier_report_is_ignored() -> None:
    assert _is_verifier_report(".verifier/reports/example.json")
    assert _is_verifier_report(".verifier/reports/verifier_report_test-001.json")
    assert not _is_verifier_report("scripts/verifier_runner.py")
    assert not _is_verifier_report("tests/test_verifier_runner.py")
    assert not _is_verifier_report("src/main.py")
