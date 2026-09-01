"""E1-S6D: Live-mode guard regression tests.

Locks the live-mode guard contract for agents/proactive_runner.py.
No live send is wired — these tests verify the guard holds permanently.

Contract:
  1. py -3.11 -m agents.proactive_runner --live  -> exit 1, NOT IMPLEMENTED
  2. --live blocked even with JARVIS_PROACTIVE_ENABLED=1
  3. run_once(dry_run=False) -> raises RuntimeError mentioning E1-S4
  4. Error message clearly states live delivery not implemented until E1-S4
  5. Default dry-run path still exits 0
  6. No Telegram/network imports in runner module
  7. --dry-run + --live together -> non-zero exit (mutually exclusive)
  8. Unknown args -> non-zero exit
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.proactive_runner import _LIVE_NOT_IMPLEMENTED, main, run_once

_RUNNER_SRC = Path(__file__).parent.parent / "agents" / "proactive_runner.py"


# ---------------------------------------------------------------------------
# 1. --live CLI blocked without env
# ---------------------------------------------------------------------------

def test_live_cli_blocked_without_env(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main(["--live"])
    assert code == 1, f"Expected exit 1, got {code}"
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["sent"] is False
    assert "NOT IMPLEMENTED" in data["error"]


# ---------------------------------------------------------------------------
# 2. --live CLI blocked even with JARVIS_PROACTIVE_ENABLED=1
# ---------------------------------------------------------------------------

def test_live_cli_blocked_with_env_enabled(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "1"}, clear=False):
        code = main(["--live"])
    assert code == 1, "--live must always exit 1 until E1-S4; env var must not unblock it"
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["sent"] is False


# ---------------------------------------------------------------------------
# 3. run_once(dry_run=False) raises RuntimeError
# ---------------------------------------------------------------------------

def test_run_once_dry_run_false_raises():
    with pytest.raises(RuntimeError):
        run_once(dry_run=False)


def test_run_once_dry_run_false_raises_regardless_of_env():
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "1"}, clear=False):
        with pytest.raises(RuntimeError):
            run_once(dry_run=False)


# ---------------------------------------------------------------------------
# 4. Error message mentions E1-S4
# ---------------------------------------------------------------------------

def test_live_error_mentions_e1_s4():
    with pytest.raises(RuntimeError) as exc_info:
        run_once(dry_run=False)
    assert "E1-S4" in str(exc_info.value), (
        "RuntimeError must mention E1-S4 so the caller knows what gate to pass"
    )


def test_live_not_implemented_constant_mentions_e1_s4():
    assert "E1-S4" in _LIVE_NOT_IMPLEMENTED


def test_live_not_implemented_constant_mentions_not_implemented():
    assert "NOT IMPLEMENTED" in _LIVE_NOT_IMPLEMENTED.upper()


# ---------------------------------------------------------------------------
# 5. Default dry-run still exits 0
# ---------------------------------------------------------------------------

def test_default_dry_run_still_exits_0(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main([])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["dry_run"] is True
    assert data["sent"] is False


def test_explicit_dry_run_flag_still_exits_0(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main(["--dry-run"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True


# ---------------------------------------------------------------------------
# 6. No Telegram / network imports in runner module
# ---------------------------------------------------------------------------

def test_no_live_sender_or_telegram_imports_in_runner():
    tree = ast.parse(_RUNNER_SRC.read_text(encoding="utf-8"))
    forbidden = {"telegram", "requests", "httpx", "urllib", "aiohttp"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for bad in forbidden:
                    assert bad not in alias.name.lower(), f"forbidden import: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module:
                for bad in forbidden:
                    assert bad not in node.module.lower(), f"forbidden import from {node.module}"


def test_no_live_send_function_defined_in_runner():
    tree = ast.parse(_RUNNER_SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name_lower = node.name.lower()
            assert "send" not in name_lower or "sender" in name_lower, (
                f"Unexpected send-related function: {node.name}"
            )


# ---------------------------------------------------------------------------
# 7. --dry-run + --live together -> non-zero (mutually exclusive)
# ---------------------------------------------------------------------------

def test_conflicting_dry_run_and_live_rejected():
    code = main(["--dry-run", "--live"])
    assert code != 0, "--dry-run and --live together must not succeed"


# ---------------------------------------------------------------------------
# 8. Unknown args -> non-zero
# ---------------------------------------------------------------------------

def test_unknown_arg_rejected():
    code = main(["--send-now"])
    assert code != 0, "Unknown flag must not succeed"


def test_unknown_positional_rejected():
    code = main(["foobar"])
    assert code != 0, "Unexpected positional arg must not succeed"
