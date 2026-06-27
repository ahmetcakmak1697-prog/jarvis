"""E1-S6A: proactive_runner.py dry-run CLI regression tests.

Covers Codex-reviewed contract:
1.  dry-run mode: sent=False, no sender called
2.  dry-run with JARVIS_PROACTIVE_ENABLED=0: decision=suppress, plan_status=None
3.  dry-run with JARVIS_PROACTIVE_ENABLED=1: decision=deliver, plan_status=ready
4.  result dict has all required keys
5.  run_once(dry_run=False) raises RuntimeError — live not implemented
6.  main(["--live"]) always returns 1 with "NOT IMPLEMENTED" error (Concern A)
7.  main([]) returns 0 with valid JSON output
8.  main(["--dry-run"]) returns 0 (explicit flag works)
9.  main(["--dry-run", "--live"]) returns non-zero (mutually exclusive, Concern C)
10. main(["--unknown-flag"]) returns non-zero (unknown arg rejected, Concern C)
11. run_once is one-shot: returns immediately without blocking
12. plan is None when decision is suppress
13. subprocess: `py -3.11 -m agents.proactive_runner` emits valid JSON, exits 0 (Blocker fix)
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.proactive_runner import _LIVE_NOT_IMPLEMENTED, main, run_once

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_with_env(enabled: str, **kwargs):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": enabled}, clear=False):
        return run_once(**kwargs)


# ---------------------------------------------------------------------------
# Test 1: dry-run always returns sent=False
# ---------------------------------------------------------------------------

def test_dry_run_sent_is_false():
    result = _run_with_env("0")
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# Test 2: disabled env → suppress, plan_status=None
# ---------------------------------------------------------------------------

def test_dry_run_disabled_env_suppresses():
    result = _run_with_env("0")
    assert result["decision"] == "suppress"
    assert result["reason"] == "proactive_disabled"
    assert result["plan_status"] is None


# ---------------------------------------------------------------------------
# Test 3: enabled env → deliver, plan_status=ready, sent still False (dry-run)
# ---------------------------------------------------------------------------

def test_dry_run_enabled_env_delivers():
    result = _run_with_env("1", dry_run=True)
    assert result["decision"] == "deliver"
    assert result["plan_status"] == "ready"
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# Test 4: result dict has all required keys
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {"ts", "dry_run", "decision", "reason", "priority", "plan_status", "sent"}

def test_result_dict_has_required_keys():
    result = _run_with_env("0")
    missing = _REQUIRED_KEYS - result.keys()
    assert not missing, f"Missing keys: {missing}"


# ---------------------------------------------------------------------------
# Test 5: run_once(dry_run=False) raises RuntimeError (Concern B)
# ---------------------------------------------------------------------------

def test_run_once_live_raises_not_implemented():
    with pytest.raises(RuntimeError, match="NOT IMPLEMENTED"):
        run_once(dry_run=False)


def test_run_once_live_error_message_mentions_e1_s4():
    with pytest.raises(RuntimeError) as exc_info:
        run_once(dry_run=False)
    assert "E1-S4" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 6: --live always returns 1 regardless of env var (Concern A)
# ---------------------------------------------------------------------------

def test_main_live_blocked_without_env(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main(["--live"])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert "NOT IMPLEMENTED" in err["error"]
    assert err["sent"] is False


def test_main_live_blocked_even_with_env_set(capsys):
    """--live is always blocked in E1-S6A, even if JARVIS_PROACTIVE_ENABLED=1."""
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "1"}, clear=False):
        code = main(["--live"])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert "NOT IMPLEMENTED" in err["error"]


# ---------------------------------------------------------------------------
# Test 7: main([]) returns 0 with valid JSON
# ---------------------------------------------------------------------------

def test_main_default_returns_0_with_json(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main([])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True
    assert data["sent"] is False


# ---------------------------------------------------------------------------
# Test 8: --dry-run explicit flag works
# ---------------------------------------------------------------------------

def test_main_explicit_dry_run_flag(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main(["--dry-run"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True


# ---------------------------------------------------------------------------
# Test 9: --dry-run and --live together → non-zero (mutually exclusive, Concern C)
# ---------------------------------------------------------------------------

def test_main_rejects_dry_run_and_live_together():
    code = main(["--dry-run", "--live"])
    assert code != 0, "Conflicting --dry-run --live must not succeed"


# ---------------------------------------------------------------------------
# Test 10: unknown arg → non-zero (Concern C)
# ---------------------------------------------------------------------------

def test_main_rejects_unknown_flag():
    code = main(["--unknown-flag"])
    assert code != 0, "Unknown flag must not succeed"


# ---------------------------------------------------------------------------
# Test 11: run_once is one-shot — does not block
# ---------------------------------------------------------------------------

def test_run_once_returns_immediately():
    results: list = []
    errors: list = []

    def _run():
        try:
            results.append(_run_with_env("0"))
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=5.0)
    assert not t.is_alive(), "run_once blocked — did not return within 5 seconds"
    assert not errors, f"run_once raised: {errors}"
    assert results


# ---------------------------------------------------------------------------
# Test 12: plan is None when suppressed
# ---------------------------------------------------------------------------

def test_plan_is_none_when_suppressed():
    result = _run_with_env("0")
    assert result["plan_status"] is None


# ---------------------------------------------------------------------------
# Test 13: subprocess — module invocation emits valid JSON, exits 0 (Blocker fix)
# ---------------------------------------------------------------------------

def test_subprocess_module_invocation_exits_0():
    proc = subprocess.run(
        [sys.executable, "-m", "agents.proactive_runner"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env={**__import__("os").environ, "JARVIS_PROACTIVE_ENABLED": "0"},
    )
    assert proc.returncode == 0, (
        f"Expected exit 0, got {proc.returncode}.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )


def test_subprocess_module_invocation_stdout_is_valid_json():
    proc = subprocess.run(
        [sys.executable, "-m", "agents.proactive_runner"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env={**__import__("os").environ, "JARVIS_PROACTIVE_ENABLED": "0"},
    )
    data = json.loads(proc.stdout)
    missing = _REQUIRED_KEYS - data.keys()
    assert not missing, f"Missing keys in subprocess output: {missing}"
    assert data["dry_run"] is True
    assert data["sent"] is False
