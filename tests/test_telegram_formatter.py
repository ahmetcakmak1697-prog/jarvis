"""Telegram HTML formatter tests."""
from __future__ import annotations


def test_plain_text_escaped():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "a < b & c > d", "source": "ollama", "latency_ms": 100})
    assert "a &lt; b &amp; c &gt; d" in result
    assert "a < b & c > d" not in result


def test_malicious_html_escaped():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "<b>fake</b><script>alert(1)</script>", "source": "ollama", "latency_ms": 10})
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


def test_code_block_in_pre():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "Ornek:\n```python\nprint('hello')\n```", "source": "ollama", "latency_ms": 500})
    assert "<pre>" in result


def test_code_block_escapes_html_inside():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "```python\nif a < b and c > d:\n    pass\n```", "source": "ollama", "latency_ms": 10})
    assert "<pre>" in result
    assert "a &lt; b" in result
    assert "c &gt; d" in result


def test_inline_code_wrapped():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "Bunun icin `print()` kullan.", "source": "ollama", "latency_ms": 10})
    assert "<code>print()</code>" in result


def test_unclosed_fence_no_crash():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "Kod:\n```python\nprint('hello')", "source": "ollama", "latency_ms": 10})
    assert isinstance(result, str) and "print" in result


def test_kc_source_label():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": "220W.", "source": "knowledge_card", "latency_ms": 5})
    assert "Hafiza" in result


def test_blocked_response():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": False, "blocked": True, "source": "redacted_blocked", "answer": "Hassas veri."})
    assert "Hassas" in result


def test_error_response_escaped():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": False, "source": "ollama_error", "error": "timeout <bad>"})
    assert "timeout" in result and "&lt;bad&gt;" in result and "<bad>" not in result


def test_none_answer_no_literal():
    from tools.telegram_formatter import format_ask_response
    result = format_ask_response({"ok": True, "answer": None, "source": "ollama", "latency_ms": 1})
    assert "None" not in result and isinstance(result, str)


def test_long_split():
    from tools.telegram_formatter import split_message
    parts = split_message("x" * 5000)
    assert len(parts) > 1 and all(len(p) <= 4096 for p in parts)
    assert "".join(parts) == "x" * 5000


def test_short_not_split():
    from tools.telegram_formatter import split_message
    assert len(split_message("Kisa.")) == 1


def test_split_prefers_newline():
    from tools.telegram_formatter import split_message
    text = "satir\n" * 900
    parts = split_message(text, limit=1000)
    assert all(len(p) <= 1000 for p in parts) and "".join(parts) == text


def test_format_messages_tag_balance():
    from tools.telegram_formatter import format_ask_messages
    big_code = "```python\n" + "x = 1\n" * 2000 + "```"
    parts = format_ask_messages({"ok": True, "answer": big_code, "source": "ollama", "latency_ms": 10})
    assert len(parts) >= 1
    for part in parts:
        assert len(part) <= 4096
        assert part.count("<pre>") == part.count("</pre>")
        assert part.count("<code>") == part.count("</code>")
