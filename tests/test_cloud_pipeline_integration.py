"""Cloud pipeline integration tests without real network calls.

These tests use real Jarvis orchestration classes and mock only network edges:
- real AssistantExecutor
- real LocalFirstRouter
- real ExecutionPolicy
- real ExecutorRegistry
- real APIExecutor
- real APIExecutorSyncAdapter
- mocked LiteLLM-style API client
- mocked local Ollama execution edge
"""
from __future__ import annotations


class FakeLiteLLMClient:
    def __init__(self, text="API pipeline cevabi.", raise_exc=None):
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


class LocalFallbackExecutor:
    def __init__(self, text="Yerel fallback cevabi."):
        self.text = text
        self.calls = []

    def generate(self, prompt, level="L2", **kwargs):
        self.calls.append({"prompt": prompt, "level": level, "kwargs": kwargs})
        return {
            "ok": True,
            "text": self.text,
            "model": "local-fallback-model",
            "level": level,
            "latency_ms": 3,
        }


def _integration_question() -> str:
    return (
        "1B7 benzersiz entegrasyon testi icin derinlemesine kapsamli "
        "mimari analiz et, riskleri rapor hazirla ve tasarla."
    )


def _build_cloud_executor(api_client, local_executor):
    from agents.api_executor import APIExecutor
    from agents.api_executor_adapter import APIExecutorSyncAdapter
    from agents.executor_registry import ExecutorRegistry

    api_executor = APIExecutor(client=api_client)
    api_adapter = APIExecutorSyncAdapter(api_executor=api_executor)

    return ExecutorRegistry(
        executors={
            "api": api_adapter,
            "ollama": local_executor,
        }
    )


def test_real_pipeline_routes_l3_cloud_to_api_without_network():
    from agents.assistant_executor import AssistantExecutor
    from agents.execution_policy import ExecutionPolicy
    from agents.local_first_router import LocalFirstRouter

    api_client = FakeLiteLLMClient(text="Bulut API entegrasyon cevabi.")
    local_executor = LocalFallbackExecutor(text="Bu cevap kullanilmamali.")
    registry = _build_cloud_executor(api_client, local_executor)

    executor = AssistantExecutor(
        router=LocalFirstRouter(),
        execution_policy=ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"}),
        executor_registry=registry,
    )

    result = executor.ask(_integration_question())

    assert result["ok"] is True
    assert result["source"] == "api"
    assert result["answer"] == "Bulut API entegrasyon cevabi."
    assert result["level"] == "L3"
    assert result["execution_decision"]["destination"] == "cloud_api"
    assert result["execution_decision"]["primary_executor"] == "api"
    assert result["execution_decision"]["fallback_executor"] == "ollama"
    assert len(api_client.calls) == 1
    assert local_executor.calls == []


def test_real_pipeline_api_timeout_falls_back_to_local_without_crashing():
    from agents.assistant_executor import AssistantExecutor
    from agents.execution_policy import ExecutionPolicy
    from agents.local_first_router import LocalFirstRouter

    api_client = FakeLiteLLMClient(raise_exc=TimeoutError("simulated provider timeout"))
    local_executor = LocalFallbackExecutor(text="API timeout sonrasi yerel cevap.")
    registry = _build_cloud_executor(api_client, local_executor)

    executor = AssistantExecutor(
        router=LocalFirstRouter(),
        execution_policy=ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"}),
        executor_registry=registry,
    )

    result = executor.ask(_integration_question())

    assert result["ok"] is True
    assert result["source"] == "ollama"
    assert result["answer"] == "API timeout sonrasi yerel cevap."
    assert result["level"] == "L3"
    assert result["primary_failed_executor"] == "api"
    assert result["execution_decision"]["destination"] == "cloud_api"
    assert len(api_client.calls) == 1
    assert len(local_executor.calls) == 1
