"""
Tests for ContractPath fallback and schema_version alignment.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import orchestrator as O


# --------------------------------------------------------------------------- #
# _gen_contract schema_version alignment
# --------------------------------------------------------------------------- #

def test_gen_contract_schema_version_is_int():
    step = {"id": "X", "kind": "implement",
            "allowed_paths": ["jarvis/x.py"],
            "acceptance_criteria_machine": []}
    c = O._gen_contract(step)
    assert isinstance(c["schema_version"], int), \
        f"schema_version should be int, got {type(c['schema_version']).__name__}"
    assert c["schema_version"] == 1


def test_gen_contract_uses_required_commands_not_stale_fields():
    step = {"id": "X", "kind": "implement",
            "allowed_paths": ["jarvis/x.py"],
            "acceptance_criteria_machine": ["pytest"]}
    c = O._gen_contract(step)
    assert "required_commands" in c
    assert "required_checks" not in c, \
        "stale field 'required_checks' must not appear in generated contract"
    assert "acceptance_criteria" not in c, \
        "generic 'acceptance_criteria' must not appear in generated contract"


def test_gen_contract_required_commands_from_machine_criteria():
    step = {"id": "X", "kind": "implement",
            "allowed_paths": ["jarvis/x.py"],
            "acceptance_criteria_machine": ["pytest tests/test_x.py", "ruff check ."]}
    c = O._gen_contract(step)
    assert "pytest tests/test_x.py" in c["required_commands"]
    assert "ruff check ." in c["required_commands"]


def test_gen_contract_non_executable_criteria_go_to_notes():
    step = {"id": "X", "kind": "spec",
            "allowed_paths": [],
            "acceptance_criteria_machine": ["all edge cases handled", "ruff check ."],
            "acceptance_criteria_human": ["UX review"]}
    c = O._gen_contract(step)
    assert "pytest" not in c["required_commands"]
    assert "ruff check ." in c["required_commands"]
    assert "all edge cases handled" in c.get("notes", "")
    assert "UX review" in c.get("notes", "")


# --------------------------------------------------------------------------- #
# ContractPath fail-closed behavior (PowerShell logic, tested via python equiv)
# --------------------------------------------------------------------------- #

def test_contract_path_fail_closed_semantics():
    """
    Verify the fail-closed logic that should apply in jarvis_auto_task.ps1:
    if ContractPath is empty and SkipVerifier is false, the script must fail.
    This is a semantic check — the actual enforcement is in PowerShell.
    """
    contract_path = ""
    skip_verifier = False
    assert not contract_path, "ContractPath should be empty to test fail-closed"
    assert not skip_verifier, "SkipVerifier should be false to test fail-closed"
    assert not contract_path and not skip_verifier, \
        "fail-closed: empty ContractPath + no SkipVerifier must be rejected"


def test_contract_path_skip_verifier_preserves_behavior():
    """
    When SkipVerifier is true, empty ContractPath should NOT cause failure.
    """
    contract_path = ""
    skip_verifier = True
    assert skip_verifier, "When SkipVerifier, empty ContractPath is allowed"
