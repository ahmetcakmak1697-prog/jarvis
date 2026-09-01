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


def test_contract_with_bom_loads_ok(tmp_path: Path) -> None:
    data = {"task_id": "bom-001", "goal": "bom test"}
    p = tmp_path / "bom_contract.json"
    bom = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
    p.write_bytes(bom)
    result = _load_contract(p)
    assert result["task_id"] == "bom-001"


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
    label = "api_" + "key"
    f.write_text(f'{label} = "supersecretvalue12345"', encoding="utf-8")
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
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    footer = "-----END " + "RSA PRIVATE KEY-----"
    f.write_text(f"{header}\nabc\n{footer}", encoding="utf-8")
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


# ---------------------------------------------------------------------------
# _parse_pytest_collected_count
# ---------------------------------------------------------------------------


def test_parse_collected_count_typical() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "collected 658 items\n\nsome_test.py ...."
    assert _parse_pytest_collected_count(output) == 658


def test_parse_collected_count_singular() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "collected 1 item"
    assert _parse_pytest_collected_count(output) == 1


def test_parse_collected_count_plural() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "collected 42 items"
    assert _parse_pytest_collected_count(output) == 42


def test_parse_collected_count_missing_returns_none() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "no tests collected"
    assert _parse_pytest_collected_count(output) is None

    output2 = ""
    assert _parse_pytest_collected_count(output2) is None


def test_parse_collected_count_empty_output() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    assert _parse_pytest_collected_count("") is None
    assert _parse_pytest_collected_count("  ") is None


# ---------------------------------------------------------------------------
# _make_report — pytest collection guard
# ---------------------------------------------------------------------------


def test_pytest_collection_absent_does_not_add_fields() -> None:
    contract: dict[str, Any] = {"task_id": "t-001", "goal": "x"}
    report = _make_report(contract, [], [], [], (None, None, None))
    assert "minimum_pytest_collected" not in report
    assert "actual_pytest_collected" not in report
    assert "pytest_collection_error" not in report
    assert report["verdict"] == "PASS"


def test_pytest_collection_zero_does_not_add_fields() -> None:
    contract: dict[str, Any] = {"task_id": "t-002", "goal": "x", "minimum_pytest_collected": 0}
    report = _make_report(contract, [], [], [], (None, None, None))
    assert "minimum_pytest_collected" not in report
    assert report["verdict"] == "PASS"


def test_pytest_collection_below_minimum_fails() -> None:
    contract: dict[str, Any] = {"task_id": "t-003", "goal": "x"}
    report = _make_report(contract, [], [], [], (10, 5, None))
    assert report["verdict"] == "FAIL"
    assert report["exit_code"] == 1
    assert report["minimum_pytest_collected"] == 10
    assert report["actual_pytest_collected"] == 5
    assert report["pytest_collection_error"] is None


def test_pytest_collection_equal_minimum_passes() -> None:
    contract: dict[str, Any] = {"task_id": "t-004", "goal": "x"}
    report = _make_report(contract, [], [], [], (10, 10, None))
    assert report["verdict"] == "PASS"
    assert report["exit_code"] == 0


def test_pytest_collection_above_minimum_passes() -> None:
    contract: dict[str, Any] = {"task_id": "t-005", "goal": "x"}
    report = _make_report(contract, [], [], [], (10, 15, None))
    assert report["verdict"] == "PASS"
    assert report["exit_code"] == 0


def test_pytest_collection_error_safe_fail() -> None:
    contract: dict[str, Any] = {"task_id": "t-006", "goal": "x"}
    report = _make_report(contract, [], [], [], (10, None, "collection command crashed"))
    assert report["verdict"] == "FAIL"
    assert report["exit_code"] == 1
    assert report["pytest_collection_error"] == "collection command crashed"


def test_pytest_collection_combined_with_path_errors() -> None:
    contract: dict[str, Any] = {"task_id": "t-007", "goal": "x"}
    report = _make_report(contract, ["forbidden_file"], [], [], (10, 50, None))
    assert report["verdict"] == "FAIL"
    assert "path_violations" in report


def test_verifier_report_is_ignored() -> None:
    assert _is_verifier_report(".verifier/reports/example.json")
    assert _is_verifier_report(".verifier/reports/verifier_report_test-001.json")
    assert not _is_verifier_report("scripts/verifier_runner.py")
    assert not _is_verifier_report("tests/test_verifier_runner.py")
    assert not _is_verifier_report("src/main.py")


# ---------------------------------------------------------------------------
# _parse_pytest_collected_count — extended formats
# ---------------------------------------------------------------------------


def test_parse_collected_count_tests_collected_in() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "671 tests collected in 1.23s"
    assert _parse_pytest_collected_count(output) == 671


def test_parse_collected_count_items_collected() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "671 items collected"
    assert _parse_pytest_collected_count(output) == 671


def test_parse_collected_count_collected_items() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "collected 671 items"
    assert _parse_pytest_collected_count(output) == 671


def test_parse_collected_count_singular_test() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    output = "1 test collected"
    assert _parse_pytest_collected_count(output) == 1


def test_parse_collected_count_combined_stderr() -> None:
    from scripts.verifier_runner import _parse_pytest_collected_count

    combined = "warnings filter...\n\n671 tests collected in 1.23s\nsome stderr line"
    assert _parse_pytest_collected_count(combined) == 671


# ---------------------------------------------------------------------------
# Fallback nodeid counting
# ---------------------------------------------------------------------------


def test_fallback_count_nodeids_normal() -> None:
    from scripts.verifier_runner import _fallback_count_nodeids

    output = "tests/test_a.py::test_foo\ntests/test_b.py::test_bar"
    assert _fallback_count_nodeids(output) == 2


def test_fallback_count_nodeids_empty() -> None:
    from scripts.verifier_runner import _fallback_count_nodeids

    output = "no tests collected\n"
    assert _fallback_count_nodeids(output) is None


def test_fallback_count_nodeids_skips_header_lines() -> None:
    from scripts.verifier_runner import _fallback_count_nodeids

    output = "<Module tests/test_x.py>\n  <Function test_x>\ntests/test_x.py::test_x"
    assert _fallback_count_nodeids(output) == 1


# ---------------------------------------------------------------------------
# Regression: verifier's own test file must not trigger _scan_for_secrets
# ---------------------------------------------------------------------------


def test_own_test_file_no_secret_leaks() -> None:
    this_file = Path(__file__)
    leaks = _scan_for_secrets([this_file])
    assert len(leaks) == 0, f"own test file should not trigger secrets: {leaks}"


# ---------------------------------------------------------------------------
# Runtime-built fake secret still triggers detection in a temp file
# ---------------------------------------------------------------------------


def test_runtime_built_api_key_detected(tmp_path: Path) -> None:
    f = tmp_path / "env.txt"
    key = "sk-" + "a" * 30
    f.write_text(key, encoding="utf-8")
    leaks = _scan_for_secrets([f])
    assert len(leaks) >= 1


def test_runtime_built_private_key_detected(tmp_path: Path) -> None:
    f = tmp_path / "key.pem"
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    body = "abcdefghijklmnopqrstuvwxyz123456"
    f.write_text(f"{header}\n{body}", encoding="utf-8")
    leaks = _scan_for_secrets([f])
    assert len(leaks) >= 1
