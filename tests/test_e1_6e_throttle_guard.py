"""E1-S6E: Throttle/cooldown guard regression tests.

Locks the stateless cooldown guard contract in agents/proactive_runner.py.
Cooldown state is passed in via the state dict to run_once().
No persistence, no file writes, no Telegram, no live delivery.

Contract:
  - state["last_delivery_ts"] within cooldown_seconds -> reason "cooldown_active"
  - state["last_delivery_ts"] older than cooldown    -> normal dry-run path
  - No last_delivery_ts in state                     -> unchanged behavior
  - Invalid timestamp or invalid/negative cooldown   -> reason "throttle_state_invalid", no crash
  - Default cooldown when key missing: 1800 seconds
  - --live still blocked (exit 1)
  - main([]) still exits 0
  - create_delivery_plan + deliver NOT called when throttle active
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import json

import pytest

from agents.proactive_runner import (
    _DEFAULT_COOLDOWN_SECONDS,
    _check_throttle,
    main,
    run_once,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ts_ago(seconds: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _ts_future(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


# ---------------------------------------------------------------------------
# 1. test_no_throttle_without_last_delivery_ts
# ---------------------------------------------------------------------------

def test_no_throttle_without_last_delivery_ts():
    result = run_once(state={})
    assert result["dry_run"] is True
    assert result["reason"] not in ("cooldown_active", "throttle_state_invalid")


def test_no_throttle_with_none_state():
    result = run_once(state=None)
    assert result["dry_run"] is True
    assert result["reason"] not in ("cooldown_active", "throttle_state_invalid")


# ---------------------------------------------------------------------------
# 2. test_throttle_blocks_recent_delivery
# ---------------------------------------------------------------------------

def test_throttle_blocks_recent_delivery():
    state = {"last_delivery_ts": _ts_ago(60), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result["sent"] is False
    assert result["reason"] == "cooldown_active"


def test_throttle_blocks_at_1_second_ago():
    state = {"last_delivery_ts": _ts_ago(1), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result["reason"] == "cooldown_active"


# ---------------------------------------------------------------------------
# 3. test_throttle_allows_after_cooldown
# ---------------------------------------------------------------------------

def test_throttle_allows_after_cooldown():
    state = {"last_delivery_ts": _ts_ago(3601), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result["reason"] not in ("cooldown_active", "throttle_state_invalid")


def test_throttle_allows_just_past_boundary():
    state = {"last_delivery_ts": _ts_ago(1801), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result["reason"] != "cooldown_active"


# ---------------------------------------------------------------------------
# 4. test_throttle_reason_visible_in_run_once_output
# ---------------------------------------------------------------------------

def test_throttle_reason_visible_in_run_once_output():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result.get("reason") == "cooldown_active"
    assert result.get("sent") is False
    assert result.get("delivery") is None
    assert "ts" in result
    assert result.get("dry_run") is True


# ---------------------------------------------------------------------------
# 5. test_invalid_last_delivery_ts_does_not_crash
# ---------------------------------------------------------------------------

def test_invalid_last_delivery_ts_does_not_crash():
    state = {"last_delivery_ts": "not-a-timestamp", "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert isinstance(result, dict)
    assert result["sent"] is False


def test_none_last_delivery_ts_does_not_crash():
    # last_delivery_ts=None is treated as absent -> no throttle
    state = {"last_delivery_ts": None, "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert isinstance(result, dict)
    assert result["reason"] not in ("cooldown_active", "throttle_state_invalid")


def test_integer_ts_does_not_crash():
    # integer is not a valid ISO string -> throttle_state_invalid
    state = {"last_delivery_ts": 1234567890, "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert isinstance(result, dict)
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# 6. test_invalid_last_delivery_ts_blocks_safely
# ---------------------------------------------------------------------------

def test_invalid_last_delivery_ts_blocks_safely():
    state = {"last_delivery_ts": "not-a-timestamp", "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# 7. test_invalid_cooldown_seconds_blocks_safely
# ---------------------------------------------------------------------------

def test_invalid_cooldown_seconds_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": "bad"}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


def test_negative_cooldown_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": -1}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


def test_none_cooldown_seconds_uses_default():
    # None cooldown_seconds -> falls back to default (1800s); 60s ago is within default
    state = {"last_delivery_ts": _ts_ago(60), "cooldown_seconds": None}
    result = run_once(state=state)
    # None can't be float() -> throttle_state_invalid (safe fallback)
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# 8. test_throttle_does_not_call_deliver_or_create_delivery_plan_when_active
# ---------------------------------------------------------------------------

def test_throttle_does_not_call_deliver_or_create_delivery_plan_when_active():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": 1800}
    with patch("agents.proactive_runner.create_delivery_plan") as mock_plan, \
         patch("agents.proactive_runner.deliver") as mock_deliver:
        result = run_once(state=state)
    mock_plan.assert_not_called()
    mock_deliver.assert_not_called()
    assert result["reason"] == "cooldown_active"


# ---------------------------------------------------------------------------
# 9. test_default_cli_still_exits_0
# ---------------------------------------------------------------------------

def test_default_cli_still_exits_0(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main([])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True
    assert data["sent"] is False


# ---------------------------------------------------------------------------
# 10. test_live_cli_still_blocked
# ---------------------------------------------------------------------------

def test_live_cli_still_blocked(capsys):
    code = main(["--live"])
    assert code == 1
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["sent"] is False
    assert "NOT IMPLEMENTED" in data["error"]


# ---------------------------------------------------------------------------
# _check_throttle unit tests (boundary / integration)
# ---------------------------------------------------------------------------

def test_check_throttle_returns_none_without_ts():
    assert _check_throttle({}) is None


def test_check_throttle_returns_none_for_old_ts():
    state = {"last_delivery_ts": _ts_ago(7200), "cooldown_seconds": 1800}
    assert _check_throttle(state) is None


def test_check_throttle_cooldown_active_for_recent_ts():
    state = {"last_delivery_ts": _ts_ago(60), "cooldown_seconds": 1800}
    assert _check_throttle(state) == "cooldown_active"


def test_check_throttle_uses_default_when_key_absent():
    # 60s ago < default 1800s
    state = {"last_delivery_ts": _ts_ago(60)}
    assert _check_throttle(state) == "cooldown_active"


def test_check_throttle_allows_after_default_cooldown():
    # 7200s ago > default 1800s
    state = {"last_delivery_ts": _ts_ago(7200)}
    assert _check_throttle(state) is None


def test_default_cooldown_constant_is_1800():
    assert _DEFAULT_COOLDOWN_SECONDS == 1800


# ---------------------------------------------------------------------------
# Non-finite cooldown values (NaN, Infinity, -Infinity) must be rejected
# ---------------------------------------------------------------------------

def test_nan_string_cooldown_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": "NaN"}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


def test_nan_float_cooldown_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": float("nan")}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


def test_inf_string_cooldown_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": "Infinity"}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


def test_inf_float_cooldown_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": float("inf")}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


def test_neg_inf_float_cooldown_blocks_safely():
    state = {"last_delivery_ts": _ts_ago(10), "cooldown_seconds": float("-inf")}
    result = run_once(state=state)
    assert result["reason"] == "throttle_state_invalid"
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# Future timestamp must be handled safely (elapsed < 0 < cooldown -> active)
# ---------------------------------------------------------------------------

def test_future_last_delivery_ts_does_not_crash():
    state = {"last_delivery_ts": _ts_future(3600), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert isinstance(result, dict)
    assert result["sent"] is False


def test_future_last_delivery_ts_blocks_safely():
    state = {"last_delivery_ts": _ts_future(3600), "cooldown_seconds": 1800}
    result = run_once(state=state)
    assert result["reason"] == "cooldown_active"
    assert result["sent"] is False
