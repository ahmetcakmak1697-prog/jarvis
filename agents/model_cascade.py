"""Y1 - ModelCascade.

Selects the appropriate model level for a given question.

Level mapping:
  L0 = local_memory  / free      - KnowledgeCard + VectorMemory hit
  L1 = local_small   / free      - small local model (quick answers)
  L2 = local_main    / cheap     - main local model (standard)
  L3 = research      / moderate  - powerful local/controlled model
  L4 = external      / expensive - premium API (last resort, force only)

Rules:
  - L4 is NEVER selected automatically; only via force_level.
  - L3 is the ceiling for complex questions.
  - CostLedger bypass is NOT this module's concern;
    caller (LocalFirstRouter) must gate external calls separately.

Scope (negative):
- No API calls
- No VectorMemory writes
- No cost consumption
- No Telegram
- Pure selection logic
"""
from __future__ import annotations

from typing import Any

_LEVELS = {
    "L0": {"model": "local_memory", "cost_tier": "free"},
    "L1": {"model": "local_small",  "cost_tier": "free"},
    "L2": {"model": "local_main",   "cost_tier": "cheap"},
    "L3": {"model": "research",     "cost_tier": "moderate"},
    "L4": {"model": "external",     "cost_tier": "expensive"},
}

_DEEP_SIGNALS = [
    # Gercekten agir / arastirma gerektiren sinyaller
    "derinlemesine", "kapsamli", "analiz et", "rapor hazirla",
    "mimarisi", "tasarim", "karsilastir", "fark nedir",
    "deep", "comprehensive", "analyze", "architecture", "research",
]

_SIMPLE_SIGNALS = [
    # Selamlama ve tek kelimelik onaylar
    "merhaba", "selam", "hi", "hello", "tamam", "ok", "evet", "hayir",
    "tesekkur", "sagol", "naber", "iyi",
]


def _tr_fold(s: str) -> str:
    s = s.replace("\u0130", "i").replace("\u0131", "i")
    s = s.replace("\u015f", "s").replace("\u015e", "s")
    s = s.replace("\u011f", "g").replace("\u011e", "g")
    s = s.replace("\u00fc", "u").replace("\u00dc", "u")
    s = s.replace("\u00f6", "o").replace("\u00d6", "o")
    s = s.replace("\u00e7", "c").replace("\u00c7", "c")
    return s.lower()


class ModelCascade:
    """Select model level for a question. Pure logic, no side effects."""

    def select(
        self,
        question: str,
        force_level: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return level selection dict."""

        # force_level always respected (caller's responsibility to gate)
        if force_level and force_level in _LEVELS:
            info = _LEVELS[force_level]
            return {
                "level": force_level,
                "model": info["model"],
                "cost_tier": info["cost_tier"],
                "reason": f"force_level:{force_level}",
            }

        folded = _tr_fold(str(question or ""))
        word_count = len(folded.split())

        # Simple short greeting ? L1
        if any(sig in folded for sig in _SIMPLE_SIGNALS) and word_count <= 4:
            return self._result("L1", "simple_greeting")

        # Deep/research signals ? L3
        if any(sig in folded for sig in _DEEP_SIGNALS):
            return self._result("L3", "deep_research_signal")

        # Long question ? L2
        if word_count >= 10:
            return self._result("L2", "long_question")

        # Default ? L2
        return self._result("L2", "default")

    def _result(self, level: str, reason: str) -> dict[str, Any]:
        info = _LEVELS[level]
        return {
            "level": level,
            "model": info["model"],
            "cost_tier": info["cost_tier"],
            "reason": reason,
        }
