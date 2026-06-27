"""E1-S4 smoke sender — concrete HTTP send function for the one-off smoke test.

Isolated here so proactive_runner.py stays import-clean at module level
(the E1-S6D AST test forbids urllib/requests/telegram imports in runner.py).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def make_telegram_http_send_fn(token: str, chat_id: str):
    """Return send_fn(text: str) -> None that POSTs to Telegram Bot API.

    Uses only stdlib urllib — no extra dependencies. Exactly one HTTP request.
    Raises sanitized RuntimeError on all failure paths — never exposes token/chat_id.

    Raises:
      RuntimeError("telegram_send_failed")   — network/urlopen error
      RuntimeError("telegram_response_invalid") — response body not valid JSON
      RuntimeError("telegram_api_error")     — Telegram ok != true
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send_fn(text: str) -> None:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(url, data=data, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read()
        except Exception:
            # Swallow original exception — its message may contain the token via URL
            raise RuntimeError("telegram_send_failed")

        try:
            parsed = json.loads(body)
        except Exception:
            raise RuntimeError("telegram_response_invalid")

        if not parsed.get("ok"):
            raise RuntimeError("telegram_api_error")

    return send_fn
