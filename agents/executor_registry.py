"""ExecutorRegistry - lazy executor lookup for Jarvis engines.

Purpose:
- Keep AssistantExecutor from hardcoding every possible engine.
- Support injected test executors.
- Support lazy factories for real executors.
- Provide execution order from policy decisions.

Scope:
- No model calls during registry construction.
- No API calls during registry construction.
- No routing decisions.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping


Factory = Callable[[], Any]


class ExecutorRegistry:
    """Small lazy registry for execution engines."""

    def __init__(
        self,
        *,
        executors: Mapping[str, Any] | None = None,
        factories: Mapping[str, Factory] | None = None,
        ollama_url: str | None = None,
    ) -> None:
        self._executors: dict[str, Any] = dict(executors or {})
        self._factories: dict[str, Factory] = dict(factories or {})

        if "ollama" not in self._executors and "ollama" not in self._factories:
            self._factories["ollama"] = lambda: self._make_ollama_executor(ollama_url)

        if "api" not in self._executors and "api" not in self._factories:
            self._factories["api"] = self._make_api_executor

    def _make_ollama_executor(self, ollama_url: str | None = None) -> Any:
        from agents.ollama_executor import OllamaExecutor
        return OllamaExecutor(ollama_url=ollama_url)

    def _make_api_executor(self) -> Any:
        from agents.api_executor import APIExecutor
        from agents.api_executor_adapter import APIExecutorSyncAdapter
        return APIExecutorSyncAdapter(api_executor=APIExecutor())

    def available_keys(self) -> list[str]:
        return sorted(set(self._executors) | set(self._factories))

    def get(self, key: str) -> Any:
        name = str(key or "").strip()
        if not name:
            raise KeyError("empty executor key")

        if name in self._executors:
            return self._executors[name]

        factory = self._factories.get(name)
        if factory is None:
            raise KeyError(name)

        executor = factory()
        self._executors[name] = executor
        return executor

    def execution_order(self, decision: dict[str, Any] | None) -> list[str]:
        decision = decision or {}
        raw = [
            decision.get("primary_executor"),
            decision.get("fallback_executor"),
        ]

        order: list[str] = []
        seen: set[str] = set()
        for item in raw:
            key = str(item or "").strip()
            if not key or key in seen:
                continue
            order.append(key)
            seen.add(key)
        return order
