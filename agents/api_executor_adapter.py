"""APIExecutorSyncAdapter - sync bridge for async APIExecutor.

AssistantExecutor is currently synchronous. APIExecutor is async because
external provider calls are network I/O. This adapter keeps async behavior
contained so the sync orchestration path does not accidentally receive a
coroutine object.

Scope:
- No provider selection
- No routing
- No real API call by itself
- No event-loop nesting
"""
from __future__ import annotations

import asyncio
from typing import Any


class APIExecutorSyncAdapter:
    """Synchronous adapter around async APIExecutor.generate."""

    def __init__(self, api_executor: Any | None = None) -> None:
        if api_executor is None:
            from agents.api_executor import APIExecutor
            api_executor = APIExecutor()
        self._api_executor = api_executor

    def generate(self, prompt: str, level: str = "L3", **kwargs: Any) -> dict[str, Any]:
        """Run async APIExecutor.generate from a sync caller.

        This is intentionally refused inside an already-running event loop.
        Async frontends should call APIExecutor directly or use a future
        async AssistantExecutor path.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            raise RuntimeError(
                "APIExecutorSyncAdapter cannot run inside a running event loop"
            )

        return asyncio.run(
            self._api_executor.generate(prompt, level=level, **kwargs)
        )
