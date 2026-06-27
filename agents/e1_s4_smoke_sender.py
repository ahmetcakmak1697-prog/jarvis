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

    Uses only stdlib urllib — no extra dependencies.
    Raises on HTTP/network failure; caller handles the exception.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send_fn(text: str) -> None:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()

    return send_fn
