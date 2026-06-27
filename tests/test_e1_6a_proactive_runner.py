"""E1-S6A: proactive_runner.py dry-run CLI regression tests.

Covers:
1. dry-run mode: sent=False, no sender called
2. dry-run with JARVIS_PROACTIVE_ENABLED=0 (default): decision=suppress, plan_status=None
3. dry-run with JARVIS_PROACTIVE_ENABLED=1: policy allows delivery, plan_status=ready
4. result dict has all required keys
5. --live without env var: RuntimeError raised by _check_live_gate
6. --live with env var set: gate passes (no RuntimeError), sent=False (sender not wired)
7. main() returns 0 on dry-run success
8. main() returns 1 when --live without env var
9. run_once() is one-shot: does not loop, does not block
10. plan is None when decision is suppress
"""
from __future__ import annotations

import json
import io
from unittest.mock import patch

import pytest

from agents.proactive_runner import _check_live_gate, main, run_once


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_with_env(enabled: str | None, **kwargs):
    env = {} if enabled is None else {"JARVIS_PROACTIVE_ENABLED": enabled}
    with patch.dict("os.environ", env, clear=False):
        return run_once(**kwargs)


# ---------------------------------------------------------------------------
# Test 1: dry-run always returns sent=False
# ---------------------------------------------------------------------------

def test_dry_run_sent_is_false():
    result = _run_with_env("0")
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# Test 2: default env (disabled) → decision=suppress, plan_status=None
# ---------------------------------------------------------------------------

def test_dry_run_disabled_env_suppresses():
    result = _run_with_env("0")
    assert result["decision"] == "suppress"
    assert result["reason"] == "proactive_disabled"
    assert result["plan_status"] is None


# ---------------------------------------------------------------------------
# Test 3: env=1 → policy allows delivery, plan_status=ready
# ---------------------------------------------------------------------------

def test_dry_run_enabled_env_delivers():
    result = _run_with_env("1", dry_run=True)
    assert result["decision"] == "deliver"
    assert result["plan_status"] == "ready"
    assert result["sent"] is False  # dry-run: no actual send


# ---------------------------------------------------------------------------
# Test 4: result dict has all required keys
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {"ts", "dry_run", "decision", "reason", "priority", "plan_status", "sent"}

def test_result_dict_has_required_keys():
    result = _run_with_env("0")
    missing = _REQUIRED_KEYS - result.keys()
    assert not missing, f"Missing keys in result: {missing}"


# ---------------------------------------------------------------------------
# Test 5: --live without env var raises RuntimeError
# ---------------------------------------------------------------------------

def test_check_live_gate_raises_without_env():
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        with pytest.raises(RuntimeError, match="LIVE MODE BLOCKED"):
            _check_live_gate()


def test_check_live_gate_raises_when_env_missing():
    env = {k: v for k, v in __import__("os").environ.items()
           if k != "JARVIS_PROACTIVE_ENABLED"}
    with patch.dict("os.environ", env, clear=True):
        with pytest.raises(RuntimeError, match="LIVE MODE BLOCKED"):
            _check_live_gate()


# ---------------------------------------------------------------------------
# Test 6: --live with env=1 → gate passes, sent=False (sender not wired)
# ---------------------------------------------------------------------------

def test_live_mode_with_env_passes_gate_but_does_not_send():
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "1"}, clear=False):
        _check_live_gate()  # must not raise
        result = run_once(dry_run=False)
        assert result["sent"] is False  # live sender not wired in E1-S6A


# ---------------------------------------------------------------------------
# Test 7: main() returns 0 on dry-run success
# ---------------------------------------------------------------------------

def test_main_returns_0_on_dry_run(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main([])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["dry_run"] is True
    assert data["sent"] is False


# ---------------------------------------------------------------------------
# Test 8: main() returns 1 when --live without env var
# ---------------------------------------------------------------------------

def test_main_returns_1_on_live_without_env(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main(["--live"])
    assert code == 1
    captured = capsys.readouterr()
    err = json.loads(captured.err)
    assert "LIVE MODE BLOCKED" in err["error"]
    assert err["sent"] is False


# ---------------------------------------------------------------------------
# Test 9: run_once is one-shot — returns immediately, does not block
# ---------------------------------------------------------------------------

def test_run_once_returns_immediately():
    import threading
    results = []
    errors = []

    def _run():
        try:
            r = _run_with_env("0")
            results.append(r)
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=5.0)
    assert not t.is_alive(), "run_once blocked — did not return within 5 seconds"
    assert not errors, f"run_once raised: {errors}"
    assert results, "run_once returned no result"


# ---------------------------------------------------------------------------
# Test 10: plan is None when decision is suppress
# ---------------------------------------------------------------------------

def test_plan_is_none_when_suppressed():
    result = _run_with_env("0")
    assert result["plan_status"] is None, (
        "plan_status must be None when decision is suppress (no plan created)"
    )
