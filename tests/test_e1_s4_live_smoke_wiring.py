"""E1-S4 live Telegram smoke wiring tests.

Verifies the E1-S4 smoke path in proactive_runner.py.
No actual Telegram messages are sent — all send_fn calls are mocked.

Contract:
  - default runner (main []) still dry-run, exit 0
  - normal --live still blocked (exit 1, NOT IMPLEMENTED)
  - --e1-s4-smoke missing token -> exit 1, reason "missing_token"
  - --e1-s4-smoke missing chat_id -> exit 1, reason "missing_chat_id"
  - smoke path calls send_fn exactly once with correct message text
  - token / chat_id values never appear in result output
  - no retry on send error
  - --e1-s4-smoke conflicts with --dry-run and --live (mutex group)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.proactive_runner import (
    _E1_S4_SMOKE_MESSAGE,
    main,
    run_e1_s4_smoke,
)

_FAKE_TOKEN = "fake-bot-token-test"
_FAKE_CHAT_ID = "987654321"


# ---------------------------------------------------------------------------
# Regression: existing paths unchanged
# ---------------------------------------------------------------------------

def test_default_runner_still_dry_run_exit_0(capsys):
    with patch.dict("os.environ", {"JARVIS_PROACTIVE_ENABLED": "0"}, clear=False):
        code = main([])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True
    assert data["sent"] is False


def test_normal_live_flag_still_blocked(capsys):
    code = main(["--live"])
    assert code == 1
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["sent"] is False
    assert "NOT IMPLEMENTED" in data["error"]


# ---------------------------------------------------------------------------
# --e1-s4-smoke CLI: missing credentials fail closed
# ---------------------------------------------------------------------------

def test_smoke_flag_missing_token_exits_with_error(capsys):
    env = {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": _FAKE_CHAT_ID}
    with patch.dict("os.environ", env, clear=False):
        code = main(["--e1-s4-smoke"])
    assert code == 1
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["sent"] is False
    assert data["reason"] == "missing_token"


def test_smoke_flag_missing_chat_id_exits_with_error(capsys):
    env = {"TELEGRAM_BOT_TOKEN": _FAKE_TOKEN, "TELEGRAM_CHAT_ID": ""}
    with patch.dict("os.environ", env, clear=False):
        code = main(["--e1-s4-smoke"])
    assert code == 1
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["sent"] is False
    assert data["reason"] == "missing_chat_id"


# ---------------------------------------------------------------------------
# run_e1_s4_smoke: credential validation (injected params)
# ---------------------------------------------------------------------------

def test_run_e1_s4_smoke_missing_token_fails_closed():
    result = run_e1_s4_smoke(send_fn=MagicMock(), token="", chat_id=_FAKE_CHAT_ID)
    assert result["sent"] is False
    assert result["reason"] == "missing_token"


def test_run_e1_s4_smoke_missing_chat_id_fails_closed():
    result = run_e1_s4_smoke(send_fn=MagicMock(), token=_FAKE_TOKEN, chat_id="")
    assert result["sent"] is False
    assert result["reason"] == "missing_chat_id"


def test_run_e1_s4_smoke_missing_token_does_not_call_sender():
    mock_send = MagicMock()
    run_e1_s4_smoke(send_fn=mock_send, token="", chat_id=_FAKE_CHAT_ID)
    mock_send.assert_not_called()


def test_run_e1_s4_smoke_missing_chat_id_does_not_call_sender():
    mock_send = MagicMock()
    run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id="")
    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Smoke path: exactly one message, correct text
# ---------------------------------------------------------------------------

def test_smoke_sends_exactly_one_message():
    mock_send = MagicMock()
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["sent"] is True
    mock_send.assert_called_once()


def test_smoke_message_text_matches_runbook():
    mock_send = MagicMock()
    run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    text_sent = mock_send.call_args[0][0]
    assert text_sent == _E1_S4_SMOKE_MESSAGE
    assert "E1-S4" in text_sent
    assert "smoke test" in text_sent.lower()
    assert "live delivery path works" in text_sent.lower()


def test_e1_s4_smoke_message_constant_content():
    assert "E1-S4" in _E1_S4_SMOKE_MESSAGE
    assert "smoke test" in _E1_S4_SMOKE_MESSAGE.lower()
    assert "live delivery path works" in _E1_S4_SMOKE_MESSAGE.lower()


# ---------------------------------------------------------------------------
# Security: token and chat_id values not in result
# ---------------------------------------------------------------------------

def test_token_value_not_in_smoke_result():
    mock_send = MagicMock()
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    result_str = json.dumps(result)
    assert _FAKE_TOKEN not in result_str


def test_chat_id_value_not_in_smoke_result():
    mock_send = MagicMock()
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    result_str = json.dumps(result)
    assert _FAKE_CHAT_ID not in result_str


def test_result_token_field_is_hint_not_value():
    mock_send = MagicMock()
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["token"].startswith("SET hidden length=")
    assert _FAKE_TOKEN not in result["token"]


def test_result_chat_id_field_is_hint_not_value():
    mock_send = MagicMock()
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["chat_id"].startswith("SET hidden length=")
    assert _FAKE_CHAT_ID not in result["chat_id"]


# ---------------------------------------------------------------------------
# Error handling: no retry on send failure
# ---------------------------------------------------------------------------

def test_no_retry_on_send_error():
    mock_send = MagicMock(side_effect=OSError("network error"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["sent"] is False
    assert result["reason"] == "send_error"
    mock_send.assert_called_once()


def test_send_error_does_not_expose_token():
    mock_send = MagicMock(side_effect=OSError("network error"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert _FAKE_TOKEN not in json.dumps(result)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_smoke_result_has_required_fields_on_success():
    mock_send = MagicMock()
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    for field in ("sent", "reason", "ts", "token", "chat_id", "message"):
        assert field in result, f"missing field: {field}"


def test_smoke_result_has_required_fields_on_failure():
    result = run_e1_s4_smoke(send_fn=MagicMock(), token="", chat_id=_FAKE_CHAT_ID)
    for field in ("sent", "reason", "ts", "token", "chat_id", "error"):
        assert field in result, f"missing field: {field}"


# ---------------------------------------------------------------------------
# Argparse: mutex group enforcement
# ---------------------------------------------------------------------------

def test_e1_s4_smoke_flag_conflict_with_dry_run():
    code = main(["--e1-s4-smoke", "--dry-run"])
    assert code != 0


def test_e1_s4_smoke_flag_conflict_with_live():
    code = main(["--e1-s4-smoke", "--live"])
    assert code != 0
