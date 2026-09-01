"""Provider smoke guard for real-provider readiness checks.

Purpose:
- Validate provider API key shape before any real provider call.
- Allow only a static, zero-risk smoke prompt.
- Keep smoke output free of prompt/response content.
- Never execute a real network call unless explicitly requested.

Manual usage:
    python -m agents.provider_smoke --provider deepseek_v4_flash
    python -m agents.provider_smoke --provider deepseek_v4_flash --execute

The first command is a preflight only. The second command can perform a real
provider call if the API key is valid and provider config allows it.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any


STATIC_SMOKE_PROMPT = "ping"
STATIC_SMOKE_SYSTEM_PROMPT = "Reply with pong only."

_PLACEHOLDER_MARKERS = (
    "TODO",
    "YOUR_KEY",
    "YOUR_API_KEY",
    "YOUR_KEY_HERE",
    "CHANGE_ME",
    "REPLACE_ME",
    "INSERT_KEY",
    "PASTE_KEY",
    "DUMMY_KEY",
)


class ProviderSmokeGuard:
    """Safe preflight/smoke guard for API providers."""

    def __init__(
        self,
        *,
        api_executor: Any | None = None,
        min_key_length: int = 12,
    ) -> None:
        if api_executor is None:
            from agents.api_executor import APIExecutor
            api_executor = APIExecutor()
        self._api_executor = api_executor
        self._min_key_length = int(min_key_length)

    def _resolve_provider(self, provider: str | None, level: str) -> Any | None:
        return self._api_executor.resolve_provider(provider=provider, level=level)

    def _validate_provider_key(self, resolved_provider: Any | None) -> dict[str, Any]:
        if resolved_provider is None:
            return {
                "ok": False,
                "stage": "provider",
                "error": "Provider could not be resolved",
            }

        env_name = getattr(resolved_provider, "api_key_env", None)
        if not env_name:
            return {
                "ok": False,
                "stage": "api_key",
                "provider": getattr(resolved_provider, "name", None),
                "model": getattr(resolved_provider, "model", None),
                "error": "Provider does not declare api_key_env",
            }

        raw_value = os.environ.get(str(env_name))
        key = raw_value.strip() if isinstance(raw_value, str) else ""

        if not key:
            return {
                "ok": False,
                "stage": "api_key",
                "provider": getattr(resolved_provider, "name", None),
                "model": getattr(resolved_provider, "model", None),
                "api_key_env": str(env_name),
                "error": f"Missing or blank API key environment variable: {env_name}",
            }

        upper_key = key.upper()
        if len(key) < self._min_key_length or any(marker in upper_key for marker in _PLACEHOLDER_MARKERS):
            return {
                "ok": False,
                "stage": "api_key",
                "provider": getattr(resolved_provider, "name", None),
                "model": getattr(resolved_provider, "model", None),
                "api_key_env": str(env_name),
                "error": f"Invalid-looking API key environment variable: {env_name}",
            }

        return {
            "ok": True,
            "stage": "api_key",
            "provider": getattr(resolved_provider, "name", None),
            "model": getattr(resolved_provider, "model", None),
            "api_key_env": str(env_name),
        }

    def run(
        self,
        *,
        provider: str | None = "deepseek_v4_flash",
        level: str = "L3",
        execute: bool = False,
    ) -> dict[str, Any]:
        """Run safe preflight, optionally followed by one real static smoke call.

        The prompt is intentionally not configurable. This prevents real user
        content from leaking into smoke tests.
        """
        resolved_provider = self._resolve_provider(provider, level)
        key_result = self._validate_provider_key(resolved_provider)
        if not key_result.get("ok"):
            key_result["executed"] = False
            return key_result

        if not execute:
            return {
                "ok": True,
                "executed": False,
                "stage": "preflight",
                "provider": key_result.get("provider"),
                "model": key_result.get("model"),
                "api_key_env": key_result.get("api_key_env"),
                "message": "Smoke preflight passed; real provider call not executed.",
            }

        from agents.api_executor_adapter import APIExecutorSyncAdapter

        adapter = APIExecutorSyncAdapter(api_executor=self._api_executor)
        result = adapter.generate(
            STATIC_SMOKE_PROMPT,
            level=level,
            provider=provider,
            system_prompt=STATIC_SMOKE_SYSTEM_PROMPT,
            privacy_level="PUBLIC",
            no_cache=True,
            no_store=True,
        )

        safe = {
            "ok": bool(result.get("ok")),
            "executed": True,
            "stage": "provider_call",
            "provider": result.get("provider") or key_result.get("provider"),
            "model": result.get("model") or key_result.get("model"),
            "level": result.get("level") or level,
            "latency_ms": result.get("latency_ms"),
            "cost_estimate": result.get("cost_estimate"),
        }

        if result.get("ok"):
            safe["response_chars"] = len(str(result.get("text") or ""))
        else:
            safe["error"] = result.get("error", "Provider smoke call failed")

        return safe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run safe provider smoke preflight/call.")
    parser.add_argument("--provider", default="deepseek_v4_flash")
    parser.add_argument("--level", default="L3")
    parser.add_argument("--execute", action="store_true", help="Perform the real static smoke call.")
    args = parser.parse_args(argv)

    result = ProviderSmokeGuard().run(
        provider=args.provider,
        level=args.level,
        execute=bool(args.execute),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
