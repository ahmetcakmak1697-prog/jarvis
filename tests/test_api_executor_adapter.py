import pytest

from agents.api_executor_adapter import APIExecutorSyncAdapter


class FakeAsyncAPIExecutor:
    def __init__(self):
        self.calls = []

    async def generate(self, prompt, level="L3", **kwargs):
        self.calls.append({"prompt": prompt, "level": level, "kwargs": kwargs})
        return {
            "ok": True,
            "text": "API cevabi",
            "model": "fake-api-model",
            "provider": "fake_provider",
            "level": level,
            "latency_ms": 12,
            "cost_estimate": None,
        }


def test_api_executor_sync_adapter_returns_dict():
    api = FakeAsyncAPIExecutor()
    adapter = APIExecutorSyncAdapter(api_executor=api)

    result = adapter.generate("Soru?", level="L3", privacy_level="CODE")

    assert result["ok"] is True
    assert result["text"] == "API cevabi"
    assert result["provider"] == "fake_provider"
    assert api.calls == [
        {
            "prompt": "Soru?",
            "level": "L3",
            "kwargs": {"privacy_level": "CODE"},
        }
    ]


def test_api_executor_sync_adapter_rejects_running_event_loop():
    api = FakeAsyncAPIExecutor()
    adapter = APIExecutorSyncAdapter(api_executor=api)

    async def call_inside_loop():
        return adapter.generate("Soru?", level="L3")

    with pytest.raises(RuntimeError) as exc:
        import asyncio
        asyncio.run(call_inside_loop())

    assert "running event loop" in str(exc.value).lower()
