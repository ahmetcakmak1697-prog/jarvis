"""E1-S4 live Telegram smoke wiring tests.

Verifies the E1-S4 smoke path in proactive_runner.py.
No actual Telegram messages are sent — all send_fn calls are mocked.

Contract:
  - default runner (main []) still dry-run, exit 0
  - normal --live still blocked (exit 1, NOT IMPLEMENTED)
  - --e1-s4-smoke missing token -> exit 1, reason "missing_token"
  - --e1-s4-smoke missing chat_id -> exit 1, reason "missing_chat_id"
  - smoke path calls send_fn exactly once with correct message text
  - token / chat_id values never appear in result output (even on error paths)
  - error field is sanitized (type name only, not exception message)
  - no retry on send error
  - --e1-s4-smoke conflicts with --dry-run and --live (mutex group)
  - concrete HTTP sender: ok=true succeeds, ok=false raises, malformed raises
  - concrete HTTP sender: network exception raises sanitized RuntimeError
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from agents.e1_s4_smoke_sender import make_telegram_http_send_fn
from agents.proactive_runner import (
    _E1_S4_SMOKE_MESSAGE,
    main,
    run_e1_s4_smoke,
)


def _make_urlopen_mock(body_bytes: bytes):
    """Return a mock suitable for patching urllib.request.urlopen as context manager."""
    resp = MagicMock()
    resp.read.return_value = body_bytes
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=resp)

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


# ---------------------------------------------------------------------------
# Secret-bearing exceptions must not leak token or chat_id
# ---------------------------------------------------------------------------

def test_secret_bearing_exception_does_not_expose_token():
    secret_token = "super-secret-bot-token-xyz"
    mock_send = MagicMock(side_effect=RuntimeError(f"error: token={secret_token}"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=secret_token, chat_id=_FAKE_CHAT_ID)
    assert secret_token not in json.dumps(result)


def test_secret_bearing_exception_does_not_expose_chat_id():
    secret_chat_id = "112233445566"
    mock_send = MagicMock(side_effect=RuntimeError(f"failed for chat {secret_chat_id}"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=secret_chat_id)
    assert secret_chat_id not in json.dumps(result)


def test_error_field_is_type_name_not_exception_message():
    mock_send = MagicMock(side_effect=RuntimeError("secret-token value chat-id"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["error"] == "RuntimeError"
    assert "secret-token value chat-id" not in result["error"]


def test_send_error_reason_is_send_error():
    mock_send = MagicMock(side_effect=ValueError("any error"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["reason"] == "send_error"


def test_send_error_sent_is_false():
    mock_send = MagicMock(side_effect=Exception("any"))
    result = run_e1_s4_smoke(send_fn=mock_send, token=_FAKE_TOKEN, chat_id=_FAKE_CHAT_ID)
    assert result["sent"] is False


# ---------------------------------------------------------------------------
# Concrete HTTP sender: response validation
# ---------------------------------------------------------------------------

def test_concrete_sender_ok_true_succeeds():
    send_fn = make_telegram_http_send_fn("tok", "chat")
    mock_open = _make_urlopen_mock(b'{"ok": true, "result": {}}')
    with patch("urllib.request.urlopen", mock_open):
        send_fn("hello")  # must not raise


def test_concrete_sender_ok_false_raises():
    send_fn = make_telegram_http_send_fn("tok", "chat")
    mock_open = _make_urlopen_mock(b'{"ok": false, "description": "Bad Request"}')
    with patch("urllib.request.urlopen", mock_open):
        with pytest.raises(RuntimeError) as exc_info:
            send_fn("hello")
    assert str(exc_info.value) == "telegram_api_error"


def test_concrete_sender_malformed_json_raises():
    send_fn = make_telegram_http_send_fn("tok", "chat")
    mock_open = _make_urlopen_mock(b"not json at all")
    with patch("urllib.request.urlopen", mock_open):
        with pytest.raises(RuntimeError) as exc_info:
            send_fn("hello")
    assert str(exc_info.value) == "telegram_response_invalid"


def test_concrete_sender_network_exception_raises_sanitized():
    send_fn = make_telegram_http_send_fn("tok", "chat")
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        with pytest.raises(RuntimeError) as exc_info:
            send_fn("hello")
    assert str(exc_info.value) == "telegram_send_failed"


def test_concrete_sender_exception_does_not_expose_token():
    secret_token = "super-secret-tok-abc"
    send_fn = make_telegram_http_send_fn(secret_token, "chat123")
    original_exc = OSError(f"error at bot{secret_token}/sendMessage")
    with patch("urllib.request.urlopen", side_effect=original_exc):
        with pytest.raises(RuntimeError) as exc_info:
            send_fn("hello")
    assert secret_token not in str(exc_info.value)
    assert str(exc_info.value) == "telegram_send_failed"


def test_concrete_sender_urlopen_called_exactly_once_no_retry():
    send_fn = make_telegram_http_send_fn("tok", "chat")
    urlopen_mock = MagicMock(side_effect=OSError("network error"))
    with patch("urllib.request.urlopen", urlopen_mock):
        with pytest.raises(RuntimeError):
            send_fn("hello")
    urlopen_mock.assert_called_once()


def test_concrete_sender_request_params_correct():
    send_fn = make_telegram_http_send_fn("mytok", "mychat")
    mock_open = _make_urlopen_mock(b'{"ok": true}')
    with patch("urllib.request.urlopen", mock_open):
        send_fn("test message payload")
    req = mock_open.call_args[0][0]
    assert isinstance(req, urllib.request.Request)
    body_params = urllib.parse.parse_qs(req.data.decode())
    assert body_params["chat_id"] == ["mychat"]
    assert body_params["text"] == ["test message payload"]
    assert req.method == "POST"
