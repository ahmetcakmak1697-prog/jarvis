"""APIExecutor - Async external model execution layer.

FAZ 1A skeleton:
- Async-first external API executor.
- No API key is required for tests.
- No real provider call in unit tests; inject a fake client.
- LiteLLM is imported lazily only when no client is injected.
- Response cache is treated as default-off from Jarvis side.

Scope (negative):
- No router refactor
- No KnowledgeCard writes
- No CostLedger writes
- No real Gemini/DeepSeek call in tests
- No Telegram/Home Assistant/MCP side effects
"""
from __future__ import annotations

import inspect
import time
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class APIProvider:
    """External provider policy/config entry."""

    name: str
    provider: str
    model: str
    role: str
    allowed_privacy: tuple[str, ...]
    cost_gate: str = "GREEN"


_DEFAULT_PROVIDERS: dict[str, APIProvider] = {
    "gemini_flash_free": APIProvider(
        name="gemini_flash_free",
        provider="gemini",
        model="gemini/gemini-2.5-flash",
        role="public_free_worker",
        allowed_privacy=("PUBLIC", "REDACTED_LOW_RISK"),
        cost_gate="GREEN",
    ),
    "deepseek_v4_flash": APIProvider(
        name="deepseek_v4_flash",
        provider="deepseek",
        model="deepseek/deepseek-chat",
        role="cheap_primary_worker",
        allowed_privacy=("PUBLIC", "REDACTED_LOW_RISK", "PERSONAL_REDACTED", "TECHNICAL", "CODE"),
        cost_gate="GREEN",
    ),
}

_LEVEL_PROVIDER_MAP: dict[str, str] = {
    "L0": "local_memory",
    "L1": "gemini_flash_free",
    "L2": "gemini_flash_free",
    "L3": "deepseek_v4_flash",
    "L4": "premium_gate_required",
}


class _LiteLLMAdapter:
    """Small adapter so APIExecutor does not depend on litellm at import time."""

    async def acompletion(self, **kwargs: Any) -> Any:
        import litellm  # lazy import: tests do not need litellm installed

        result = litellm.acompletion(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


class APIExecutor:
    """Execute prompts on external API models through a LiteLLM-compatible client."""

    def __init__(
        self,
        client: Any | None = None,
        provider_config: Mapping[str, APIProvider] | None = None,
        default_provider: str = "deepseek_v4_flash",
        timeout_s: float = 30.0,
        max_calls_per_request: int = 1,
    ) -> None:
        self._client = client
        self._providers = dict(provider_config or _DEFAULT_PROVIDERS)
        self._default_provider = default_provider
        self._timeout_s = timeout_s
        self._max_calls_per_request = max_calls_per_request

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._client = _LiteLLMAdapter()
        return self._client

    def providers(self) -> dict[str, APIProvider]:
        """Return a copy of provider configuration."""
        return dict(self._providers)

    def level_to_provider(self, level: str) -> str | None:
        """Map cascade level to an external provider key."""
        return _LEVEL_PROVIDER_MAP.get(str(level or "").upper(), self._default_provider)

    def resolve_provider(self, provider: str | None = None, level: str = "L3") -> APIProvider | None:
        """Resolve explicit provider or cascade level to provider config."""
        key = provider or self.level_to_provider(level) or self._default_provider
        if key in {"local_memory", "premium_gate_required"}:
            return None
        return self._providers.get(key)

    async def generate(
        self,
        prompt: str,
        level: str = "L3",
        provider: str | None = None,
        model: str | None = None,
        dry_run: bool = False,
        system_prompt: str | None = None,
        privacy_level: str = "PUBLIC",
        no_cache: bool = True,
        no_store: bool = True,
    ) -> dict[str, Any]:
        """Generate a response from an external API model.

        Returns:
            {ok, text, model, provider, level, latency_ms, cost_estimate, error?}
        """
        resolved_provider = self.resolve_provider(provider=provider, level=level)
        resolved_model = model or (resolved_provider.model if resolved_provider else None)
        provider_name = resolved_provider.name if resolved_provider else provider

        if not resolved_provider or not resolved_model:
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "provider": provider_name,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "error": f"Unknown API provider for level={level!r} provider={provider!r}",
            }

        privacy = str(privacy_level or "PUBLIC").upper()
        if privacy not in resolved_provider.allowed_privacy:
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "error": f"privacy_level {privacy!r} is not allowed for provider {resolved_provider.name!r}",
            }

        if dry_run:
            return {
                "ok": True,
                "text": "[dry_run]",
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "dry_run": True,
            }

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": str(system_prompt)})
        messages.append({"role": "user", "content": str(prompt or "")})

        headers: dict[str, str] = {}
        cache_directives: list[str] = []
        if no_cache:
            cache_directives.append("no-cache")
        if no_store:
            cache_directives.append("no-store")
        if cache_directives:
            headers["Cache-Control"] = ", ".join(cache_directives)

        t0 = time.monotonic()
        try:
            client = self._get_client()
            response = client.acompletion(
                model=resolved_model,
                messages=messages,
                timeout=self._timeout_s,
                extra_headers=headers or None,
                metadata={
                    "jarvis_provider": resolved_provider.name,
                    "jarvis_level": level,
                    "jarvis_privacy_level": privacy,
                    "jarvis_cost_gate": resolved_provider.cost_gate,
                    "jarvis_no_cache": no_cache,
                    "jarvis_no_store": no_store,
                    "jarvis_max_calls_per_request": self._max_calls_per_request,
                },
            )
            if inspect.isawaitable(response):
                response = await response

            latency_ms = int((time.monotonic() - t0) * 1000)
            text = self._extract_text(response)
            return {
                "ok": True,
                "text": text,
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": latency_ms,
                "cost_estimate": None,
            }
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": latency_ms,
                "cost_estimate": None,
                "error": str(exc),
            }

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract assistant text from common LiteLLM/OpenAI-style responses."""
        if response is None:
            return ""

        if isinstance(response, dict):
            choices = response.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0] or {}
                if isinstance(first, dict):
                    message = first.get("message") or {}
                    if isinstance(message, dict):
                        content = message.get("content")
                        if content is not None:
                            return str(content).strip()
                    if first.get("text") is not None:
                        return str(first.get("text")).strip()

            for key in ("response", "text", "content"):
                if response.get(key) is not None:
                    return str(response.get(key)).strip()

        choices = getattr(response, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            content = getattr(message, "content", None) if message is not None else None
            if content is not None:
                return str(content).strip()
            text = getattr(first, "text", None)
            if text is not None:
                return str(text).strip()

        return str(response).strip()

