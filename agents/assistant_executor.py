"""AssistantExecutor - Router + OllamaExecutor zinciri.

Jarvis'in cevap uretim hatti:
  1. LocalFirstRouter.route(question) -> karar
  2. answer_local (KC/cache/memory) -> direkt cevap don
  3. redacted_blocked / external_blocked -> guvenli ret don
  4. ask_external -> OllamaExecutor.generate(question, level) -> cevap don

Stateless: her soru bagimsiz islenir.
Conversation history C1 hafiza katmanindan gelir; bu sinif yonetmez.

Scope (negative):
- No KnowledgeCard write
- No crystallize
- No Telegram
- No telemetry store
- No LiteLLM
- No external API (sadece Ollama)
"""
from __future__ import annotations

import time
from typing import Any

def _fold_tr(s: str) -> str:
    return (
        str(s or "").strip().lower()
        .replace("\u0131", "i").replace("\u011f", "g")
        .replace("\u00fc", "u").replace("\u015f", "s")
        .replace("\u00f6", "o").replace("\u00e7", "c")
    )

_QUICK_REPLIES: dict[str, str] = {
    "merhaba": "Buradayim efendim.",
    "selam": "Buradayim efendim.",
    "selamlar": "Buradayim efendim.",
    "hey": "Buradayim efendim.",
    "naber": "Hazir efendim.",
    "nasilsin": "Sistemler nominal efendim.",
    "tamam": "Tamamdir.",
    "ok": "Tamamdir.",
    "tesekkur": "Rica ederim efendim.",
    "tesekkurler": "Rica ederim efendim.",
    "iyi": "Tamamdir.",
}

_LOCAL_ROUTES = {"knowledge_card", "memory", "cache"}
_BLOCKED_DECISIONS = {"redacted_blocked", "external_blocked"}

_BLOCKED_MESSAGES = {
    "redacted_blocked": "Bu soru hassas veri iceriyor ve disari gonderilemez.",
    "external_blocked": "Gunluk dis model limiti doldu. Daha sonra tekrar deneyin.",
}


class AssistantExecutor:
    """Orchestrates Router -> Executor pipeline. Stateless per-question."""

    def __init__(
        self,
        router=None,
        executor=None,
        ollama_url: str | None = None,
    ) -> None:
        self._router = router
        self._executor = executor
        self._ollama_url = ollama_url

    def _get_router(self):
        if self._router is not None:
            return self._router
        from agents.local_first_router import LocalFirstRouter
        self._router = LocalFirstRouter()
        return self._router

    def _get_executor(self):
        if self._executor is not None:
            return self._executor
        from agents.ollama_executor import OllamaExecutor
        self._executor = OllamaExecutor(ollama_url=self._ollama_url)
        return self._executor

    def ask(self, question: str) -> dict[str, Any]:
        """Route question and return unified response dict.

        Returns:
            ok=True  + answer + source + latency_ms  on success
            ok=False + blocked=True + source          on block
            ok=False + error + source                 on failure
        """
        t0 = time.monotonic()

        # Quick reply: deterministic, model cagirmaz
        qkey = _fold_tr(question).strip(" .!?")
        if qkey in _QUICK_REPLIES:
            return {
                "ok": True,
                "answer": _QUICK_REPLIES[qkey],
                "source": "quick_reply",
                "router_decision": {
                    "decision": "answer_local",
                    "route": "quick_reply",
                    "confidence": 100,
                    "reason": "deterministic_quick_reply",
                    "signals": {"quick_reply": True},
                },
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }

        router = self._get_router()
        rd = router.route(question)
        decision = rd.get("decision", "")
        route = rd.get("route", "")

        # --- local answer (KC / cache / memory) ---
        if decision == "answer_local" and route in _LOCAL_ROUTES:
            answer = rd.get("answer") or ""
            return {
                "ok": True,
                "answer": answer,
                "source": route,
                "router_decision": rd,
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }

        # --- blocked ---
        if decision in _BLOCKED_DECISIONS:
            return {
                "ok": False,
                "blocked": True,
                "answer": _BLOCKED_MESSAGES.get(decision, "Islem engellendi."),
                "source": decision,
                "router_decision": rd,
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }

        # --- ask external via Ollama ---
        if decision == "ask_external":
            cascade = rd.get("cascade") or {}
            level = cascade.get("level", "L2")
            executor = self._get_executor()
            exec_result = executor.generate(question, level=level)
            total_ms = int((time.monotonic() - t0) * 1000)

            if exec_result.get("ok"):
                return {
                    "ok": True,
                    "answer": exec_result.get("text", ""),
                    "source": "ollama",
                    "model": exec_result.get("model"),
                    "level": level,
                    "router_decision": rd,
                    "latency_ms": total_ms,
                    "ollama_latency_ms": exec_result.get("latency_ms"),
                }
            else:
                return {
                    "ok": False,
                    "answer": None,
                    "source": "ollama_error",
                    "error": exec_result.get("error", "Bilinmeyen hata"),
                    "level": level,
                    "router_decision": rd,
                    "latency_ms": total_ms,
                }

        # --- fallback (clarify, no_answer, unknown) ---
        return {
            "ok": False,
            "answer": None,
            "source": decision or "unknown",
            "router_decision": rd,
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }
