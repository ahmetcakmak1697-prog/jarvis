"""APIExecutor tests - external API calls must be mocked."""
from __future__ import annotations

import asyncio


class FakeLiteLLMClient:
    def __init__(self, response=None, fail=False):
        self.response = response or {
            "choices": [
                {"message": {"content": "API cevap."}}
            ]
        }
        self.fail = fail
        self.calls = []

    async def acompletion(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise ConnectionError("API baglantisi yok.")
        return self.response


def run(coro):
    return asyncio.run(coro)


def test_api_executor_imports():
    from agents.api_executor import APIExecutor

    assert APIExecutor is not None


def test_default_providers_include_gemini_and_deepseek():
    from agents.api_executor import APIExecutor

    ex = APIExecutor(client=FakeLiteLLMClient())
    providers = ex.providers()
    assert "gemini_flash_free" in providers
    assert "deepseek_v4_flash" in providers


def test_dry_run_returns_ok_without_api_call():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(ex.generate("Soru?", provider="deepseek_v4_flash", dry_run=True))

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["text"] == "[dry_run]"
    assert client.calls == []


def test_generate_normalizes_litellm_response():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient(
        response={
            "choices": [
                {"message": {"content": "DeepSeek mock cevabi."}}
            ]
        }
    )
    ex = APIExecutor(client=client)
    result = run(ex.generate("Test sorusu?", provider="deepseek_v4_flash"))

    assert result["ok"] is True
    assert result["text"] == "DeepSeek mock cevabi."
    assert result["provider"] == "deepseek_v4_flash"
    assert result["model"] is not None
    assert result["level"] == "L3"
    assert "latency_ms" in result
    assert "cost_estimate" in result


def test_generate_handles_client_error():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient(fail=True)
    ex = APIExecutor(client=client)
    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is False
    assert result["text"] is None
    assert "error" in result


def test_unknown_provider_returns_ok_false_without_call():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(ex.generate("Soru?", provider="unknown_provider"))

    assert result["ok"] is False
    assert result["text"] is None
    assert "error" in result
    assert client.calls == []


def test_privacy_guard_blocks_work_data_for_gemini_free():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(
        ex.generate(
            "ESHOT ham veri analizi",
            provider="gemini_flash_free",
            privacy_level="WORK_INTERNAL",
        )
    )

    assert result["ok"] is False
    assert "privacy_level" in result["error"]
    assert client.calls == []


def test_no_cache_no_store_headers_are_sent_by_default():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is True
    assert len(client.calls) == 1
    headers = client.calls[0]["extra_headers"]
    assert headers["Cache-Control"] == "no-cache, no-store"


def test_system_prompt_is_passed_as_system_message():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(
        ex.generate(
            "Kisa cevap ver.",
            provider="deepseek_v4_flash",
            system_prompt="Sen Jarvis'sin.",
        )
    )

    assert result["ok"] is True
    messages = client.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert "Jarvis" in messages[0]["content"]
    assert messages[1]["role"] == "user"

def test_l4_requires_premium_gate_and_does_not_call_api():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(ex.generate("Premium analiz", level="L4"))

    assert result["ok"] is False
    assert result["text"] is None
    assert "Unknown API provider" in result["error"]
    assert client.calls == []
