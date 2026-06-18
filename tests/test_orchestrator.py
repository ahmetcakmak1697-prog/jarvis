"""Tests for orchestrator.py — _read_verdict strict report reading."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from scripts.orchestrator import _gen_contract, _is_executable_criterion, _read_verdict


# ---------------------------------------------------------------------------
# _read_verdict — strict report reading
# ---------------------------------------------------------------------------


def _write_report(dir: Path, task_id: str, verdict: str, mtime: float | None = None):
    p = dir / f"verifier_report_{task_id}.json"
    p.write_text(json.dumps({"task_id": task_id, "verdict": verdict}), encoding="utf-8")
    if mtime is not None:
        os_handle = p.open("a")
        os_handle.close()
    return p


def test_read_verdict_missing_report(tmp_path: Path) -> None:
    """a) missing report -> FAIL"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    result = _read_verdict(reports_dir, "step-001", time.time())
    assert result == "FAIL"


def test_read_verdict_stale_report(tmp_path: Path) -> None:
    """b) stale report (older than run_start) -> FAIL"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    p = reports_dir / "verifier_report_step-001.json"
    p.write_text(json.dumps({"task_id": "step-001", "verdict": "PASS"}), encoding="utf-8")
    # set mtime to a known old timestamp (well before any reasonable run_start)
    OLD_MTIME = 1000000.0
    os.utime(p, (OLD_MTIME, OLD_MTIME))
    run_start = time.time()
    result = _read_verdict(reports_dir, "step-001", run_start)
    assert result == "FAIL", "stale report should be rejected"


def test_read_verdict_wrong_id(tmp_path: Path) -> None:
    """c) report with wrong task_id -> FAIL"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    # write a report for a different task_id but same filename pattern
    # verifier writes verifier_report_{task_id}.json, so a wrong id means wrong filename
    p = reports_dir / "verifier_report_wrong-id.json"
    p.write_text(json.dumps({"task_id": "wrong-id", "verdict": "PASS"}), encoding="utf-8")
    run_start = time.time()
    result = _read_verdict(reports_dir, "step-001", run_start)
    assert result == "FAIL", "report for wrong task_id should be rejected"


def test_read_verdict_fresh_matching_pass(tmp_path: Path) -> None:
    """d) fresh matching report with PASS -> PASS"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_start = time.time()
    p = reports_dir / "verifier_report_step-001.json"
    p.write_text(json.dumps({"task_id": "step-001", "verdict": "PASS"}), encoding="utf-8")
    # ensure mtime >= run_start with a small tolerance
    now = time.time()
    os_handle = p.open("a")
    os_handle.close()
    result = _read_verdict(reports_dir, "step-001", now - 2)
    assert result == "PASS"


def test_read_verdict_fresh_matching_fail(tmp_path: Path) -> None:
    """fresh matching report with FAIL -> FAIL"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_start = time.time()
    p = reports_dir / "verifier_report_step-002.json"
    p.write_text(json.dumps({"task_id": "step-002", "verdict": "FAIL"}), encoding="utf-8")
    now = time.time()
    os_handle = p.open("a")
    os_handle.close()
    result = _read_verdict(reports_dir, "step-002", now - 2)
    assert result == "FAIL"


def test_read_verdict_fresh_matching_needs_human(tmp_path: Path) -> None:
    """fresh matching report with NEEDS_HUMAN -> NEEDS_HUMAN"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    p = reports_dir / "verifier_report_step-003.json"
    p.write_text(json.dumps({"task_id": "step-003", "verdict": "NEEDS_HUMAN"}), encoding="utf-8")
    now = time.time()
    os_handle = p.open("a")
    os_handle.close()
    result = _read_verdict(reports_dir, "step-003", now - 2)
    assert result == "NEEDS_HUMAN"


def test_read_verdict_invalid_verdict_value(tmp_path: Path) -> None:
    """report with invalid verdict value -> FAIL"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    p = reports_dir / "verifier_report_step-004.json"
    p.write_text(json.dumps({"task_id": "step-004", "verdict": "INVALID"}), encoding="utf-8")
    now = time.time()
    os_handle = p.open("a")
    os_handle.close()
    result = _read_verdict(reports_dir, "step-004", now - 2)
    assert result == "FAIL", "INVALID verdict should be rejected"


def test_read_verdict_empty_reports_dir(tmp_path: Path) -> None:
    """empty reports dir -> FAIL"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    result = _read_verdict(reports_dir, "step-005", time.time())
    assert result == "FAIL"


# ---------------------------------------------------------------------------
# _is_executable_criterion
# ---------------------------------------------------------------------------


def test_is_executable_criterion_recognizes_pytest():
    assert _is_executable_criterion("pytest")
    assert _is_executable_criterion("pytest::tests/test_x.py")
    assert _is_executable_criterion("py -3.11 -m pytest tests/")


def test_is_executable_criterion_recognizes_ruff():
    assert _is_executable_criterion("ruff")
    assert _is_executable_criterion("ruff check .")


def test_is_executable_criterion_rejects_descriptive():
    assert not _is_executable_criterion("verifier: minimum_pytest_collected guard çalışıyor")
    assert not _is_executable_criterion("Audit çıktısı incelendi")


# ---------------------------------------------------------------------------
# _gen_contract — schema alignment
# ---------------------------------------------------------------------------


def test_gen_contract_includes_required_fields():
    step = {
        "id": "test-step-001",
        "title": "Test step",
        "kind": "implement",
        "allowed_paths": ["scripts/", "tests/"],
        "acceptance_criteria_machine": ["pytest::tests/test_x.py"],
        "acceptance_criteria_human": [],
        "notes": "Some notes",
    }
    contract = _gen_contract(step)
    assert contract["schema_version"] == "1.0"
    assert contract["task_id"] == "test-step-001"
    assert contract["goal"] == "Test step"
    assert "allowed_paths" in contract
    assert "forbidden_paths" in contract
    assert contract["required_commands"] == ["py -3.11 -m pytest tests/test_x.py"]
    assert "minimum_pytest_collected" in contract
    assert "human_review_required" in contract
    assert "notes" in contract
    assert "acceptance_criteria" not in contract
    assert "required_checks" not in contract


def test_gen_contract_converts_machine_criteria():
    step = {
        "id": "test-step-002",
        "title": "Convert test",
        "kind": "implement",
        "allowed_paths": ["scripts/"],
        "acceptance_criteria_machine": [
            "pytest::tests/test_a.py",
            "ruff check .",
            "verifier: some descriptive check",
        ],
        "acceptance_criteria_human": [],
        "notes": "",
    }
    contract = _gen_contract(step)
    assert "py -3.11 -m pytest tests/test_a.py" in contract["required_commands"]
    assert "ruff check ." in contract["required_commands"]
    assert "verifier: some descriptive check" in contract["notes"]


def test_gen_contract_human_criteria_in_notes():
    step = {
        "id": "test-step-003",
        "title": "Human criteria test",
        "kind": "implement",
        "allowed_paths": ["scripts/"],
        "acceptance_criteria_machine": [],
        "acceptance_criteria_human": ["Türkçe kalite iyi olmalı"],
        "notes": "",
    }
    contract = _gen_contract(step)
    assert "Türkçe kalite iyi olmalı" in contract["notes"]


def test_gen_contract_minimum_pytest_default():
    step = {
        "id": "test-step-004",
        "title": "Default test",
        "kind": "implement",
        "allowed_paths": ["scripts/"],
        "acceptance_criteria_machine": [],
        "acceptance_criteria_human": [],
    }
    contract = _gen_contract(step)
    assert contract["minimum_pytest_collected"] == 0


def test_gen_contract_human_review_for_judgment():
    step = {
        "id": "test-step-005",
        "title": "Judgment test",
        "kind": "architectural",
        "allowed_paths": ["docs/"],
        "acceptance_criteria_machine": [],
        "acceptance_criteria_human": [],
    }
    contract = _gen_contract(step)
    assert contract["human_review_required"] is True


def test_gen_contract_no_acceptance_criteria_orphans():
    step = {
        "id": "test-step-006",
        "title": "No orphans",
        "kind": "implement",
        "allowed_paths": ["scripts/"],
        "acceptance_criteria_machine": [],
        "acceptance_criteria_human": [],
        "notes": "",
    }
    contract = _gen_contract(step)
    assert "acceptance_criteria" not in contract
    assert "required_checks" not in contract
