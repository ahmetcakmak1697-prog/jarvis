"""Provider smoke CLI tests.

No real network calls are performed here.
"""
from __future__ import annotations

import json


def _parse_json_output(capsys):
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def test_provider_smoke_cli_missing_key_returns_nonzero_without_execute(monkeypatch, capsys):
    from agents.provider_smoke import main

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    code = main(["--provider", "deepseek_v4_flash"])

    result = _parse_json_output(capsys)
    assert code == 1
    assert result["ok"] is False
    assert result["executed"] is False
    assert "DEEPSEEK_API_KEY" in result["error"]


def test_provider_smoke_cli_preflight_valid_key_returns_zero_without_execute(monkeypatch, capsys):
    from agents.provider_smoke import main

    monkeypatch.setenv("DEEPSEEK_API_KEY", "valid-deepseek-key-123")

    code = main(["--provider", "deepseek_v4_flash"])

    result = _parse_json_output(capsys)
    assert code == 0
    assert result["ok"] is True
    assert result["executed"] is False
    assert result["stage"] == "preflight"
    assert "ping" not in str(result)
    assert "pong" not in str(result)


def test_provider_smoke_cli_placeholder_key_returns_nonzero(monkeypatch, capsys):
    from agents.provider_smoke import main

    monkeypatch.setenv("DEEPSEEK_API_KEY", "YOUR_KEY_HERE")

    code = main(["--provider", "deepseek_v4_flash"])

    result = _parse_json_output(capsys)
    assert code == 1
    assert result["ok"] is False
    assert result["executed"] is False
    assert "Invalid-looking" in result["error"]


def test_provider_smoke_documentation_exists_and_warns_about_execute():
    path = __import__("pathlib").Path("docs/provider_smoke.md")
    text = path.read_text(encoding="utf-8").lower()

    assert "--execute" in text
    assert "ping" in text
    assert "ger?ek kullan?c? sorusu" in text
    assert "otomatik test" in text
