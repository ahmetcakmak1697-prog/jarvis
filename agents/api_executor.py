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
import ipaddress
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Mapping


PRIVACY_LEVELS = (
    "PUBLIC",
    "REDACTED_LOW_RISK",
    "PERSONAL_REDACTED",
    "TECHNICAL",
    "CODE",
    "WORK_INTERNAL",
    "LEGAL_CONFIDENTIAL",
    "FINANCIAL_PRIVATE",
    "SECRETS",
)

SENSITIVE_PRIVACY_LEVELS = (
    "WORK_INTERNAL",
    "LEGAL_CONFIDENTIAL",
    "FINANCIAL_PRIVATE",
    "SECRETS",
)

COST_GATES = ("GREEN", "YELLOW", "RED")


@dataclass(frozen=True)
class APIProvider:
    """External provider policy/config entry."""

    name: str
    provider: str
    model: str
    role: str
    allowed_privacy: tuple[str, ...]
    cost_gate: str = "GREEN"
    base_url: str | None = None
    api_key_env: str | None = None


_DEFAULT_PROVIDERS: dict[str, APIProvider] = {
    "gemini_flash_free": APIProvider(
        name="gemini_flash_free",
        provider="gemini",
        model="gemini/gemini-2.5-flash",
        role="public_free_worker",
        allowed_privacy=("PUBLIC", "REDACTED_LOW_RISK"),
        cost_gate="GREEN",
        api_key_env="GEMINI_API_KEY",
    ),
    "deepseek_v4_flash": APIProvider(
        name="deepseek_v4_flash",
        provider="deepseek",
        model="deepseek/deepseek-chat",
        role="cheap_primary_worker",
        allowed_privacy=("PUBLIC", "REDACTED_LOW_RISK", "PERSONAL_REDACTED", "TECHNICAL", "CODE"),
        cost_gate="GREEN",
        api_key_env="DEEPSEEK_API_KEY",
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
        config_path: str | Path | None = None,
        default_provider: str = "deepseek_v4_flash",
        timeout_s: float = 15.0,
        max_calls_per_request: int = 1,
    ) -> None:
        self._client = client
        if provider_config is not None:
            self._providers = dict(provider_config)
        else:
            self._providers = self._load_provider_config(config_path)
        self._default_provider = default_provider
        self._timeout_s = timeout_s
        self._max_calls_per_request = max_calls_per_request

    def _load_provider_config(self, config_path: str | Path | None) -> dict[str, APIProvider]:
        """Load provider config from JSON, falling back safely to defaults."""
        providers = dict(_DEFAULT_PROVIDERS)

        if config_path is None:
            return providers

        try:
            path = Path(config_path)
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            configured = data.get("providers", {}) if isinstance(data, dict) else {}
            if not isinstance(configured, dict):
                return providers

            for key, spec in configured.items():
                if not isinstance(key, str) or not isinstance(spec, dict):
                    continue

                allowed = spec.get("allowed_privacy", ("PUBLIC",))
                if isinstance(allowed, str):
                    allowed_privacy = (allowed,)
                else:
                    allowed_privacy = tuple(str(x) for x in allowed)

                providers[key] = APIProvider(
                    name=key,
                    provider=str(spec.get("provider", "")).strip(),
                    model=str(spec.get("model", "")).strip(),
                    role=str(spec.get("role", "")).strip(),
                    allowed_privacy=allowed_privacy,
                    cost_gate=str(spec.get("cost_gate", "GREEN")).strip().upper(),
                    base_url=(str(spec.get("base_url")).strip() if spec.get("base_url") else None),
                    api_key_env=(str(spec.get("api_key_env")).strip() if spec.get("api_key_env") else None),
                )
        except Exception:
            return providers

        return providers

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._client = _LiteLLMAdapter()
        return self._client

    def providers(self) -> dict[str, APIProvider]:
        """Return a copy of provider configuration."""
        return dict(self._providers)

    def _validate_external_base_url(self, base_url: str) -> str | None:
        """Reject unsafe external provider base URLs.

        Local network targets are not allowed for API providers. Local executors
        such as Ollama must use separate local executor paths, not APIProvider.
        """
        try:
            parsed = urlparse(base_url)
        except Exception:
            return "base_url is invalid"

        if parsed.scheme.lower() != "https":
            return "base_url must use https"

        host = (parsed.hostname or "").strip().lower()
        if not host:
            return "base_url host is required"

        if host in {"localhost", "0.0.0.0"} or host.endswith(".localhost") or host.endswith(".local"):
            return "base_url must not target local hosts"

        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return None

        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return "base_url must not target private or local IP ranges"

        return None

    def validate_provider_config(self) -> dict[str, Any]:
        """Validate provider policy/config entries without making API calls."""
        errors: list[str] = []

        for key, provider in self._providers.items():
            if not isinstance(provider, APIProvider):
                errors.append(f"{key}: provider config must be APIProvider")
                continue

            if provider.name != key:
                errors.append(f"{key}: provider.name must match config key")

            if not provider.provider:
                errors.append(f"{key}: provider is required")

            if not provider.model:
                errors.append(f"{key}: model is required")

            if not provider.role:
                errors.append(f"{key}: role is required")

            if provider.provider == "openai_compatible" and not provider.base_url:
                errors.append(f"{key}: openai_compatible provider requires base_url")

            if provider.base_url:
                base_url_error = self._validate_external_base_url(provider.base_url)
                if base_url_error:
                    errors.append(f"{key}: {base_url_error}")

            if provider.cost_gate not in COST_GATES:
                errors.append(f"{key}: invalid cost_gate {provider.cost_gate!r}")

            if not provider.allowed_privacy:
                errors.append(f"{key}: allowed_privacy cannot be empty")

            for privacy in provider.allowed_privacy:
                if privacy not in PRIVACY_LEVELS:
                    errors.append(f"{key}: unknown privacy level {privacy!r}")

            if provider.cost_gate == "GREEN" and "SECRETS" in provider.allowed_privacy:
                errors.append(f"{key}: GREEN provider cannot allow SECRETS")

        return {"ok": not errors, "errors": errors}

    def level_to_provider(self, level: str) -> str | None:
        """Map cascade level to an external provider key."""
        return _LEVEL_PROVIDER_MAP.get(str(level or "").upper(), self._default_provider)

    def resolve_provider(self, provider: str | None = None, level: str = "L3") -> APIProvider | None:
        """Resolve explicit provider or cascade level to provider config."""
        key = provider or self.level_to_provider(level) or self._default_provider
        if key in {"local_memory", "premium_gate_required"}:
            return None
        return self._providers.get(key)

    def _effective_timeout_s(self) -> float | None:
        """Return validated timeout in seconds, or None if invalid."""
        try:
            value = float(self._timeout_s)
        except (TypeError, ValueError):
            return None
        if value <= 0:
            return None
        return value

    def _resolve_api_key(self, provider: APIProvider) -> str | None:
        """Resolve provider API key from environment without storing secrets."""
        if not provider.api_key_env:
            return None
        value = os.environ.get(provider.api_key_env)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _sanitize_provider_error(self, exc: Exception, provider: APIProvider | None = None) -> str:
        """Return a safe, user-visible provider error without secrets or URLs."""
        msg = str(exc) or exc.__class__.__name__

        if provider is not None:
            resolved_key = self._resolve_api_key(provider)
            if resolved_key:
                msg = msg.replace(resolved_key, "[REDACTED_SECRET]")

        msg = re.sub(r"(?i)api[_-]?key\s*=\s*\S+", "[REDACTED_API_KEY]", msg)
        msg = re.sub(r"(?i)bearer\s+\S+", "[REDACTED_BEARER]", msg)
        msg = re.sub(r"https?://[^\s)]+", "[REDACTED_URL]", msg)

        msg = msg.strip()
        if not msg:
            msg = exc.__class__.__name__

        return f"Provider request failed safely: {msg}"[:500]

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
        route_key = provider or self.level_to_provider(level) or self._default_provider

        if route_key == "premium_gate_required":
            return {
                "ok": False,
                "text": None,
                "model": model,
                "provider": route_key,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "error": "Premium gate required for this level; explicit user approval is required.",
            }

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

        effective_timeout_s = self._effective_timeout_s()
        if effective_timeout_s is None:
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "error": "timeout_s must be a positive number",
            }

        if self._max_calls_per_request < 1:
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "error": "max_calls_per_request must be >= 1",
            }

        resolved_api_key = self._resolve_api_key(resolved_provider)
        if resolved_provider.api_key_env and not resolved_api_key and self._client is None:
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "provider": resolved_provider.name,
                "level": level,
                "latency_ms": 0,
                "cost_estimate": None,
                "error": f"Missing API key environment variable: {resolved_provider.api_key_env}",
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
            call_kwargs = {
                "model": resolved_model,
                "messages": messages,
                "timeout": effective_timeout_s,
                "extra_headers": headers or None,
                "drop_params": True,
                "metadata": {
                    "jarvis_provider": resolved_provider.name,
                    "jarvis_level": level,
                    "jarvis_privacy_level": privacy,
                    "jarvis_cost_gate": resolved_provider.cost_gate,
                    "jarvis_no_cache": no_cache,
                    "jarvis_no_store": no_store,
                    "jarvis_max_calls_per_request": self._max_calls_per_request,
                    "jarvis_api_key_env": resolved_provider.api_key_env,
                },
            }
            if resolved_provider.base_url:
                call_kwargs["api_base"] = resolved_provider.base_url
            if resolved_api_key:
                call_kwargs["api_key"] = resolved_api_key

            response = client.acompletion(**call_kwargs)
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
                "error": self._sanitize_provider_error(exc, resolved_provider),
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

