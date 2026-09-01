"""Provider smoke guard tests.

These tests do not perform real network calls.
"""
from __future__ import annotations


class FakeLiteLLMClient:
    def __init__(self, text="pong", raise_exc=None):
        self.text = text
        self.raise_exc = raise_exc
        self.calls = []

    async def acompletion(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc is not None:
            raise self.raise_exc
        return {
            "choices": [
                {
                    "message": {
                        "content": self.text,
                    }
                }
            ]
        }


def _guard_with_client(client):
    from agents.api_executor import APIExecutor
    from agents.provider_smoke import ProviderSmokeGuard

    api_executor = APIExecutor(client=client)
    return ProviderSmokeGuard(api_executor=api_executor)


def test_smoke_guard_rejects_missing_key_without_client_call(monkeypatch):
    from agents.provider_smoke import ProviderSmokeGuard
    from agents.api_executor import APIExecutor

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = FakeLiteLLMClient()
    guard = ProviderSmokeGuard(api_executor=APIExecutor(client=client))

    result = guard.run(provider="deepseek_v4_flash", execute=True)

    assert result["ok"] is False
    assert result["executed"] is False
    assert "DEEPSEEK_API_KEY" in result["error"]
    assert client.calls == []


def test_smoke_guard_rejects_placeholder_key_without_client_call(monkeypatch):
    from agents.provider_smoke import ProviderSmokeGuard
    from agents.api_executor import APIExecutor

    monkeypatch.setenv("DEEPSEEK_API_KEY", "YOUR_KEY_HERE")
    client = FakeLiteLLMClient()
    guard = ProviderSmokeGuard(api_executor=APIExecutor(client=client))

    result = guard.run(provider="deepseek_v4_flash", execute=True)

    assert result["ok"] is False
    assert result["executed"] is False
    assert "Invalid-looking" in result["error"]
    assert client.calls == []


def test_smoke_guard_preflight_does_not_call_provider(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "valid-deepseek-key-123")
    client = FakeLiteLLMClient()
    guard = _guard_with_client(client)

    result = guard.run(provider="deepseek_v4_flash", execute=False)

    assert result["ok"] is True
    assert result["executed"] is False
    assert result["stage"] == "preflight"
    assert client.calls == []


def test_smoke_guard_execute_uses_static_ping_and_suppresses_text(monkeypatch):
    from agents.provider_smoke import STATIC_SMOKE_PROMPT

    monkeypatch.setenv("DEEPSEEK_API_KEY", "valid-deepseek-key-123")
    client = FakeLiteLLMClient(text="pong")
    guard = _guard_with_client(client)

    result = guard.run(provider="deepseek_v4_flash", execute=True)

    assert result["ok"] is True
    assert result["executed"] is True
    assert result["stage"] == "provider_call"
    assert result["provider"] == "deepseek_v4_flash"
    assert result["response_chars"] == 4
    assert "text" not in result
    assert STATIC_SMOKE_PROMPT not in str(result)
    assert "pong" not in str(result)

    messages = client.calls[0]["messages"]
    assert messages[-1]["content"] == STATIC_SMOKE_PROMPT


def test_smoke_guard_execute_sanitizes_provider_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "valid-deepseek-key-123")
    client = FakeLiteLLMClient(
        raise_exc=RuntimeError(
            "Authentication failed api_key=valid-deepseek-key-123 "
            "Bearer valid-deepseek-key-123 https://api.deepseek.com/v1"
        )
    )
    guard = _guard_with_client(client)

    result = guard.run(provider="deepseek_v4_flash", execute=True)

    assert result["ok"] is False
    assert result["executed"] is True
    assert "valid-deepseek-key-123" not in result["error"]
    assert "api_key=" not in result["error"]
    assert "Bearer" not in result["error"]
    assert "https://api.deepseek.com" not in result["error"]
