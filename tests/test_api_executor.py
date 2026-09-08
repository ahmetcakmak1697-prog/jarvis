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
    assert "premium" in result["error"].lower()
    assert client.calls == []

def test_sensitive_privacy_levels_are_declared():
    from agents.api_executor import SENSITIVE_PRIVACY_LEVELS

    assert "WORK_INTERNAL" in SENSITIVE_PRIVACY_LEVELS
    assert "LEGAL_CONFIDENTIAL" in SENSITIVE_PRIVACY_LEVELS
    assert "FINANCIAL_PRIVATE" in SENSITIVE_PRIVACY_LEVELS
    assert "SECRETS" in SENSITIVE_PRIVACY_LEVELS


def test_provider_config_validation_passes_for_defaults():
    from agents.api_executor import APIExecutor

    ex = APIExecutor(client=FakeLiteLLMClient())
    result = ex.validate_provider_config()

    assert result["ok"] is True
    assert result["errors"] == []


def test_provider_config_validation_detects_bad_cost_gate():
    from agents.api_executor import APIExecutor, APIProvider

    bad_provider = APIProvider(
        name="bad",
        provider="bad",
        model="bad-model",
        role="bad-role",
        allowed_privacy=("PUBLIC",),
        cost_gate="PURPLE",
    )
    ex = APIExecutor(
        client=FakeLiteLLMClient(),
        provider_config={"bad": bad_provider},
    )

    result = ex.validate_provider_config()

    assert result["ok"] is False
    assert any("cost_gate" in err for err in result["errors"])


def test_max_calls_per_request_must_be_positive():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client, max_calls_per_request=0)
    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is False
    assert "max_calls_per_request" in result["error"]
    assert client.calls == []


def test_l4_level_is_blocked_by_premium_gate():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)
    result = run(ex.generate("En guclu modele tasinmasi gereken analiz", level="L4"))

    assert result["ok"] is False
    assert result["text"] is None
    assert "premium" in result["error"].lower()
    assert client.calls == []

def test_config_path_loads_provider_override(tmp_path):
    import json
    from agents.api_executor import APIExecutor

    config_path = tmp_path / "api_providers.json"
    config_path.write_text(
        json.dumps(
            {
                "providers": {
                    "commandcode_provider": {
                        "provider": "openai_compatible",
                        "model": "commandcode/deepseek-v4-pro",
                        "role": "coding_provider",
                        "allowed_privacy": ["PUBLIC", "TECHNICAL", "CODE"],
                        "cost_gate": "YELLOW",
                        "base_url": "https://api.commandcode.ai/provider/v1",
                        "api_key_env": "COMMANDCODE_API_KEY",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ex = APIExecutor(client=FakeLiteLLMClient(), config_path=config_path)
    providers = ex.providers()

    assert "commandcode_provider" in providers
    assert providers["commandcode_provider"].provider == "openai_compatible"
    assert providers["commandcode_provider"].base_url == "https://api.commandcode.ai/provider/v1"
    assert providers["commandcode_provider"].api_key_env == "COMMANDCODE_API_KEY"


def test_bad_config_path_falls_back_to_defaults(tmp_path):
    from agents.api_executor import APIExecutor

    config_path = tmp_path / "api_providers.json"
    config_path.write_text("{bad json", encoding="utf-8")

    ex = APIExecutor(client=FakeLiteLLMClient(), config_path=config_path)
    providers = ex.providers()

    assert "gemini_flash_free" in providers
    assert "deepseek_v4_flash" in providers


def test_openai_compatible_provider_requires_base_url():
    from agents.api_executor import APIExecutor, APIProvider

    bad_provider = APIProvider(
        name="bad_openai_compatible",
        provider="openai_compatible",
        model="some-model",
        role="coding_provider",
        allowed_privacy=("PUBLIC",),
        cost_gate="YELLOW",
    )
    ex = APIExecutor(
        client=FakeLiteLLMClient(),
        provider_config={"bad_openai_compatible": bad_provider},
    )

    result = ex.validate_provider_config()

    assert result["ok"] is False
    assert any("base_url" in err for err in result["errors"])


def test_provider_base_url_is_sent_to_client():
    from agents.api_executor import APIExecutor, APIProvider

    client = FakeLiteLLMClient()
    provider = APIProvider(
        name="commandcode_provider",
        provider="openai_compatible",
        model="commandcode/deepseek-v4-pro",
        role="coding_provider",
        allowed_privacy=("PUBLIC", "TECHNICAL", "CODE"),
        cost_gate="YELLOW",
        base_url="https://api.commandcode.ai/provider/v1",
        api_key_env="COMMANDCODE_API_KEY",
    )
    ex = APIExecutor(
        client=client,
        provider_config={"commandcode_provider": provider},
    )

    result = run(ex.generate("Kod incele", provider="commandcode_provider", privacy_level="CODE"))

    assert result["ok"] is True
    assert client.calls[0]["api_base"] == "https://api.commandcode.ai/provider/v1"


def test_api_providers_example_json_loads_and_validates():
    from pathlib import Path
    from agents.api_executor import APIExecutor

    config_path = Path("config/api_providers.example.json")
    assert config_path.exists()

    ex = APIExecutor(client=FakeLiteLLMClient(), config_path=config_path)
    result = ex.validate_provider_config()
    providers = ex.providers()

    assert result["ok"] is True
    assert result["errors"] == []
    assert "gemini_flash_free" in providers
    assert "deepseek_v4_flash" in providers
    assert "commandcode_provider" in providers
    assert providers["commandcode_provider"].base_url == "https://api.commandcode.ai/provider/v1"
    assert providers["commandcode_provider"].api_key_env == "COMMANDCODE_API_KEY"


def test_provider_api_key_env_is_resolved_and_sent_to_client(monkeypatch):
    from agents.api_executor import APIExecutor, APIProvider

    monkeypatch.setenv("COMMANDCODE_API_KEY", "test-commandcode-key")
    client = FakeLiteLLMClient()
    provider = APIProvider(
        name="commandcode_provider",
        provider="openai_compatible",
        model="commandcode/deepseek-v4-pro",
        role="coding_provider",
        allowed_privacy=("PUBLIC", "TECHNICAL", "CODE"),
        cost_gate="YELLOW",
        base_url="https://api.commandcode.ai/provider/v1",
        api_key_env="COMMANDCODE_API_KEY",
    )
    ex = APIExecutor(client=client, provider_config={"commandcode_provider": provider})

    result = run(ex.generate("Kod incele", provider="commandcode_provider", privacy_level="CODE"))

    assert result["ok"] is True
    assert client.calls[0]["api_key"] == "test-commandcode-key"
    assert client.calls[0]["api_base"] == "https://api.commandcode.ai/provider/v1"


def test_missing_api_key_env_fails_before_real_adapter_call(monkeypatch):
    from agents.api_executor import APIExecutor

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    ex = APIExecutor(client=None)
    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is False
    assert result["text"] is None
    assert "DEEPSEEK_API_KEY" in result["error"]


def test_openai_compatible_rejects_insecure_http_base_url():
    from agents.api_executor import APIExecutor, APIProvider

    provider = APIProvider(
        name="bad_http_provider",
        provider="openai_compatible",
        model="bad/model",
        role="coding_provider",
        allowed_privacy=("PUBLIC",),
        cost_gate="YELLOW",
        base_url="http://api.example.com/v1",
        api_key_env="BAD_API_KEY",
    )
    ex = APIExecutor(client=FakeLiteLLMClient(), provider_config={"bad_http_provider": provider})

    result = ex.validate_provider_config()

    assert result["ok"] is False
    assert any("https" in err.lower() for err in result["errors"])


def test_openai_compatible_rejects_localhost_base_url():
    from agents.api_executor import APIExecutor, APIProvider

    provider = APIProvider(
        name="bad_local_provider",
        provider="openai_compatible",
        model="bad/model",
        role="coding_provider",
        allowed_privacy=("PUBLIC",),
        cost_gate="YELLOW",
        base_url="https://localhost:11434/v1",
        api_key_env="BAD_API_KEY",
    )
    ex = APIExecutor(client=FakeLiteLLMClient(), provider_config={"bad_local_provider": provider})

    result = ex.validate_provider_config()

    assert result["ok"] is False
    assert any("local" in err.lower() or "private" in err.lower() for err in result["errors"])


def test_openai_compatible_rejects_private_ip_base_url():
    from agents.api_executor import APIExecutor, APIProvider

    provider = APIProvider(
        name="bad_private_provider",
        provider="openai_compatible",
        model="bad/model",
        role="coding_provider",
        allowed_privacy=("PUBLIC",),
        cost_gate="YELLOW",
        base_url="https://192.168.1.10:8080/v1",
        api_key_env="BAD_API_KEY",
    )
    ex = APIExecutor(client=FakeLiteLLMClient(), provider_config={"bad_private_provider": provider})

    result = ex.validate_provider_config()

    assert result["ok"] is False
    assert any("private" in err.lower() for err in result["errors"])


def test_completion_call_sets_drop_params_true():
    from agents.api_executor import APIExecutor, APIProvider

    client = FakeLiteLLMClient()
    provider = APIProvider(
        name="safe_provider",
        provider="openai_compatible",
        model="safe/model",
        role="coding_provider",
        allowed_privacy=("PUBLIC",),
        cost_gate="YELLOW",
        base_url="https://api.example.com/v1",
    )
    ex = APIExecutor(client=client, provider_config={"safe_provider": provider})

    result = run(ex.generate("Merhaba", provider="safe_provider"))

    assert result["ok"] is True
    assert client.calls[0]["drop_params"] is True


def test_provider_exception_error_is_sanitized(monkeypatch):
    from agents.api_executor import APIExecutor, APIProvider

    class ExplodingClient:
        async def acompletion(self, **kwargs):
            raise RuntimeError(
                "AuthenticationError api_key=test-commandcode-key "
                "Bearer test-commandcode-key "
                "https://api.commandcode.ai/provider/v1"
            )

    monkeypatch.setenv("COMMANDCODE_API_KEY", "test-commandcode-key")
    provider = APIProvider(
        name="commandcode_provider",
        provider="openai_compatible",
        model="commandcode/deepseek-v4-pro",
        role="coding_provider",
        allowed_privacy=("PUBLIC", "TECHNICAL", "CODE"),
        cost_gate="YELLOW",
        base_url="https://api.commandcode.ai/provider/v1",
        api_key_env="COMMANDCODE_API_KEY",
    )
    ex = APIExecutor(client=ExplodingClient(), provider_config={"commandcode_provider": provider})

    result = run(ex.generate("Kod incele", provider="commandcode_provider", privacy_level="CODE"))

    assert result["ok"] is False
    assert result["text"] is None
    assert "test-commandcode-key" not in result["error"]
    assert "api_key=" not in result["error"]
    assert "Bearer" not in result["error"]
    assert "https://api.commandcode.ai" not in result["error"]


def test_default_timeout_is_15_seconds():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client)

    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is True
    assert client.calls[0]["timeout"] == 15.0


def test_custom_timeout_is_sent_to_client():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client, timeout_s=7.5)

    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is True
    assert client.calls[0]["timeout"] == 7.5


def test_invalid_timeout_fails_before_client_call():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client, timeout_s=0)

    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is False
    assert "timeout_s" in result["error"]
    assert client.calls == []


def test_negative_timeout_fails_before_client_call():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client, timeout_s=-1)

    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is False
    assert "timeout_s" in result["error"]
    assert client.calls == []


def test_none_timeout_fails_before_client_call():
    from agents.api_executor import APIExecutor

    client = FakeLiteLLMClient()
    ex = APIExecutor(client=client, timeout_s=None)

    result = run(ex.generate("Soru?", provider="deepseek_v4_flash"))

    assert result["ok"] is False
    assert "timeout_s" in result["error"]
    assert client.calls == []
