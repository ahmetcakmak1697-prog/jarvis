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

import os
import time
from typing import Any

from agents.persona import build_system_prompt as _build_system_prompt


_LEVEL_ROLE_MAP = {
    "L0": "local_memory",
    "L1": "local_small",
    "L2": "local_main",
    "L3": "research_model",
}

# Persona SSOT. Daha once burada satir-ici, ASCII'ye indirgenmis ve bozuk
# kodlamali (Turkce harfler soru isaretine donusmus) uc ayri prompt
# duruyordu. Artik tek kaynak
# agents/persona.py; sozlesme kilidi tests/test_persona_ssot.py.
#
# config.py buraya import EDILMEZ: import aninda load_dotenv() cagirir ve
# HF_*_OFFLINE ortam degiskenlerini yazar (CLAUDE.md 9). Ad, sureç ortamindan
# okunur; config.py yuklenmisse zaten oradan gelmis olur.
_JARVIS_NAME = os.getenv("JARVIS_NAME", "Jarvis")

_SYSTEM_PROMPTS = {
    level: _build_system_prompt(name=_JARVIS_NAME, level=level)
    for level in ("L1", "L2", "L3")
}

_LEVEL_OPTIONS = {
    "L1": {"temperature": 0.2, "num_predict": 80},
    "L2": {"temperature": 0.2, "num_predict": 350},
    "L3": {"temperature": 0.3, "num_predict": 900},
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
                url = reg.ollama_url() if reg else "http://127.0.0.1:11434"

            class _OllamaHTTPClient:
                def __init__(self, base_url):
                    self._url = base_url.rstrip("/")

                def generate(self, model, prompt, system=None, keep_alive="5m", stream=False, **kw):
                    body = {
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "keep_alive": keep_alive,
                    }
                    if system:
                        body["system"] = system
                    payload = _json.dumps(body).encode("utf-8")
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
        resolved_model = model or self.level_to_model(level)
        if not resolved_model or resolved_model == "local_main":
            # L4+ veya bilinmeyen level icin varsayilan L2 modeli kullan
            from agents.model_registry import ModelRegistry
            try:
                resolved_model = ModelRegistry().local_main()
            except Exception:
                resolved_model = "mistral-nemo:latest"

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

        effective_system = system_prompt or _SYSTEM_PROMPTS.get(level, _SYSTEM_PROMPTS["L2"])
        full_prompt = prompt  # system native parametre olarak gidecek
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        t0 = time.monotonic()
        try:
            client = self._get_client()
            effective_options = _LEVEL_OPTIONS.get(level, _LEVEL_OPTIONS["L2"])
            response = client.generate(model=resolved_model, prompt=full_prompt, system=effective_system, keep_alive="5m", options=effective_options)
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
