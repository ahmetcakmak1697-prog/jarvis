import pytest

from agents.executor_registry import ExecutorRegistry


class DummyExecutor:
    def __init__(self, name="dummy"):
        self.name = name


def test_registry_returns_injected_executor_by_key():
    ollama = DummyExecutor("ollama")
    registry = ExecutorRegistry(executors={"ollama": ollama})

    assert registry.get("ollama") is ollama


def test_registry_factory_is_lazy():
    calls = []

    def make_api():
        calls.append("api_created")
        return DummyExecutor("api")

    registry = ExecutorRegistry(factories={"api": make_api})

    assert calls == []

    api = registry.get("api")

    assert api.name == "api"
    assert calls == ["api_created"]


def test_registry_caches_factory_result():
    calls = []

    def make_ollama():
        calls.append("ollama_created")
        return DummyExecutor("ollama")

    registry = ExecutorRegistry(factories={"ollama": make_ollama})

    first = registry.get("ollama")
    second = registry.get("ollama")

    assert first is second
    assert calls == ["ollama_created"]


def test_registry_unknown_executor_raises_key_error():
    registry = ExecutorRegistry(executors={})

    with pytest.raises(KeyError):
        registry.get("missing")


def test_registry_supports_default_executor_keys_without_instantiating():
    registry = ExecutorRegistry()

    keys = registry.available_keys()

    assert "ollama" in keys
    assert "api" in keys


def test_registry_execution_order_primary_then_fallback():
    registry = ExecutorRegistry(executors={
        "api": DummyExecutor("api"),
        "ollama": DummyExecutor("ollama"),
    })
    decision = {
        "primary_executor": "api",
        "fallback_executor": "ollama",
    }

    order = registry.execution_order(decision)

    assert order == ["api", "ollama"]


def test_registry_execution_order_deduplicates_same_fallback():
    registry = ExecutorRegistry(executors={
        "ollama": DummyExecutor("ollama"),
    })
    decision = {
        "primary_executor": "ollama",
        "fallback_executor": "ollama",
    }

    order = registry.execution_order(decision)

    assert order == ["ollama"]


def test_registry_default_api_factory_returns_sync_adapter():
    from agents.api_executor_adapter import APIExecutorSyncAdapter

    registry = ExecutorRegistry()
    api = registry.get("api")

    assert isinstance(api, APIExecutorSyncAdapter)
    assert hasattr(api, "generate")
