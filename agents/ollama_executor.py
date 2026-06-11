"""OllamaExecutor - Local model execution layer.

Executes prompts on local Ollama models based on cascade level.
Uses ModelRegistry for model name resolution.

Level mapping:
  L0 = local_memory (no model call needed)
  L1 = local_small
  L2 = local_main
  L3 = research_model

Scope (negative):
- No external API calls
- No LiteLLM
- No cache writes
- No KnowledgeCard writes
- No Telegram
"""
from __future__ import annotations

import time
from typing import Any


_LEVEL_ROLE_MAP = {
    "L0": "local_memory",
    "L1": "local_small",
    "L2": "local_main",
    "L3": "research_model",
}


class OllamaExecutor:
    """Execute prompts on local Ollama models."""

    def __init__(
        self,
        client=None,
        ollama_url: str | None = None,
        registry=None,
    ) -> None:
        self._client = client
        self._ollama_url = ollama_url
        self._registry = registry

    def _get_registry(self):
        if self._registry is not None:
            return self._registry
        try:
            from agents.model_registry import ModelRegistry
            self._registry = ModelRegistry()
        except Exception:
            self._registry = None
        return self._registry

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import urllib.request
            import json as _json

            url = self._ollama_url
            if not url:
                reg = self._get_registry()
                url = reg.ollama_url() if reg else "http://localhost:11434"

            class _OllamaHTTPClient:
                def __init__(self, base_url):
                    self._url = base_url.rstrip("/")

                def generate(self, model, prompt, stream=False):
                    payload = _json.dumps({
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        f"{self._url}/api/generate",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        return _json.loads(resp.read().decode("utf-8"))

            self._client = _OllamaHTTPClient(url)
        except Exception as exc:
            raise RuntimeError(f"Ollama client olusturulamadi: {exc}") from exc
        return self._client

    def level_to_model(self, level: str) -> str | None:
        """Map cascade level to model name via ModelRegistry."""
        role = _LEVEL_ROLE_MAP.get(str(level or "").upper())
        if role == "local_memory":
            return "local_memory"
        if role is None:
            return None
        reg = self._get_registry()
        if reg is None:
            return role
        try:
            return getattr(reg, role)()
        except Exception:
            return role

    def generate(
        self,
        prompt: str,
        level: str = "L2",
        model: str | None = None,
        dry_run: bool = False,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a response from local Ollama model.

        Returns:
            {ok, text, model, level, latency_ms, error?}
        """
        resolved_model = model or self.level_to_model(level) or "local_main"

        if dry_run:
            return {
                "ok": True,
                "text": "[dry_run]",
                "model": resolved_model,
                "level": level,
                "latency_ms": 0,
                "dry_run": True,
            }

        if resolved_model == "local_memory":
            return {
                "ok": False,
                "text": None,
                "model": "local_memory",
                "level": level,
                "latency_ms": 0,
                "error": "L0 local_memory does not require model execution.",
            }

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        t0 = time.monotonic()
        try:
            client = self._get_client()
            response = client.generate(model=resolved_model, prompt=full_prompt)
            latency_ms = int((time.monotonic() - t0) * 1000)
            text = str(response.get("response") or "").strip()
            return {
                "ok": True,
                "text": text,
                "model": resolved_model,
                "level": level,
                "latency_ms": latency_ms,
            }
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            return {
                "ok": False,
                "text": None,
                "model": resolved_model,
                "level": level,
                "latency_ms": latency_ms,
                "error": str(exc),
            }
