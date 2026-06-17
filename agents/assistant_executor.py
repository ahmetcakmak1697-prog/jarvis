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
    text = str(s or "").strip()
    text = text.replace("\u0130", "i")
    return (
        text.lower()
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
        execution_policy=None,
        executor_registry=None,
        api_budget_gate=None,
    ) -> None:
        self._router = router
        self._executor = executor
        self._ollama_url = ollama_url
        self._execution_policy = execution_policy
        self._executor_registry = executor_registry
        self._api_budget_gate = api_budget_gate

    def _log_telemetry(self, result: dict, question: str) -> None:
        try:
            from agents.telemetry_event_store import TelemetryEventStore
            store = TelemetryEventStore()
            store.log_ask(
                source=str(result.get("source") or "unknown"),
                level=result.get("level"),
                model=result.get("model"),
                ok=bool(result.get("ok")),
                blocked=bool(result.get("blocked")),
                latency_ms=int(result.get("latency_ms") or 0),
                answer_chars=len(str(result.get("answer") or "")),
                question=question,
            )
        except Exception:
            pass  # telemetry failure must never break the main flow

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

    def _get_execution_policy(self):
        if self._execution_policy is not None:
            return self._execution_policy
        from agents.execution_policy import ExecutionPolicy
        self._execution_policy = ExecutionPolicy()
        return self._execution_policy

    def _get_executor_registry(self):
        if self._executor_registry is not None:
            return self._executor_registry

        from agents.executor_registry import ExecutorRegistry

        executors = {}
        if self._executor is not None:
            # Backward compatibility: old tests and callers inject a single
            # executor, historically meaning the Ollama/local executor.
            executors["ollama"] = self._executor

        self._executor_registry = ExecutorRegistry(
            executors=executors,
            ollama_url=self._ollama_url,
        )
        return self._executor_registry

    def _check_api_budget(self, *, provider: str | None = None, level: str | None = None) -> dict[str, Any]:
        if self._api_budget_gate is None:
            return {
                "allowed": False,
                "reason": "missing_api_budget_gate",
                "provider": provider,
                "level": level,
            }
        try:
            return self._api_budget_gate.check_and_consume(provider=provider, level=level)
        except Exception as exc:
            return {
                "allowed": False,
                "reason": "budget_gate_error",
                "provider": provider,
                "level": level,
                "error": str(exc),
            }

    def _classify_for_external(self, question: str) -> tuple[str, str]:
        """Compute (data_class, privacy_level) for an external-bound question.

        Pure, cheap, no side effects. privacy_level is the old-system
        equivalent (agents.privacy_level_bridge), forwarded ONLY when the
        chosen executor is "api" -- OllamaExecutor.generate() does not
        accept a privacy_level kwarg and must never receive one.

        Fails closed: any unexpected error here returns the MOST
        restrictive old-system value, never "PUBLIC". This makes a
        classifier bug degrade into "api rejects it, fall back to
        ollama" -- the same safe outcome as a real sensitive question --
        rather than silently widening access.
        """
        try:
            from agents.data_classifier import classify
            from agents.privacy_level_bridge import data_class_to_privacy_level
            data_class = classify(question)
            privacy_level = data_class_to_privacy_level(data_class)
            return data_class, privacy_level
        except Exception:
            return "sensitive", "WORK_INTERNAL"

    def ask(self, question: str) -> dict[str, Any]:
        result = self._ask_inner(question)
        self._log_telemetry(result, question)
        return result

    def _ask_inner(self, question: str) -> dict[str, Any]:
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

        # --- ask external via execution policy + executor registry ---
        if decision == "ask_external":
            cascade = rd.get("cascade") or {}
            level = str(cascade.get("level", "L2")).upper()

            execution_decision = self._get_execution_policy().choose(rd)

            if execution_decision.get("requires_approval"):
                return {
                    "ok": False,
                    "blocked": True,
                    "answer": "Bu islem premium/onay gerektiriyor.",
                    "source": execution_decision.get("destination") or "premium_gate",
                    "level": execution_decision.get("level", level),
                    "router_decision": rd,
                    "execution_decision": execution_decision,
                    "latency_ms": int((time.monotonic() - t0) * 1000),
                }

            data_class, privacy_level = self._classify_for_external(question)

            registry = self._get_executor_registry()
            order = registry.execution_order(execution_decision)

            last_error = "Bilinmeyen hata"
            last_source = "executor_error"
            primary_failed_executor = None

            for executor_key in order:
                try:
                    executor = registry.get(executor_key)
                except KeyError:
                    if primary_failed_executor is None:
                        primary_failed_executor = str(executor_key)
                    last_error = f"Executor unavailable: {executor_key}"
                    last_source = f"{executor_key}_missing"
                    continue
                except Exception as exc:
                    if primary_failed_executor is None:
                        primary_failed_executor = str(executor_key)
                    last_error = f"Executor lookup failed: {executor_key}: {exc}"
                    last_source = f"{executor_key}_lookup_error"
                    continue

                api_budget_gate = None
                if str(executor_key) == "api":
                    api_budget_gate = self._check_api_budget(provider=str(executor_key), level=level)
                    if not api_budget_gate.get("allowed"):
                        if primary_failed_executor is None:
                            primary_failed_executor = str(executor_key)
                        last_error = f"API budget blocked: {api_budget_gate.get('reason', 'denied')}"
                        last_source = "api_budget_blocked"
                        continue

                try:
                    if str(executor_key) == "api":
                        exec_result = executor.generate(question, level=level, privacy_level=privacy_level)
                    else:
                        exec_result = executor.generate(question, level=level)
                except Exception as exc:
                    exec_result = {
                        "ok": False,
                        "text": None,
                        "model": None,
                        "level": level,
                        "latency_ms": 0,
                        "error": str(exc),
                    }

                total_ms = int((time.monotonic() - t0) * 1000)
                source = "ollama" if executor_key == "ollama" else str(executor_key)

                if exec_result.get("ok"):
                    response = {
                        "ok": True,
                        "answer": exec_result.get("text", ""),
                        "source": source,
                        "model": exec_result.get("model"),
                        "level": level,
                        "router_decision": rd,
                        "execution_decision": execution_decision,
                        "latency_ms": total_ms,
                        "data_class": data_class,
                    }
                    if executor_key == "ollama":
                        response["ollama_latency_ms"] = exec_result.get("latency_ms")
                    else:
                        response[f"{executor_key}_latency_ms"] = exec_result.get("latency_ms")
                    if executor_key == "api" and api_budget_gate is not None:
                        response["api_budget_gate"] = api_budget_gate
                    if primary_failed_executor:
                        response["primary_failed_executor"] = primary_failed_executor
                    return response

                if primary_failed_executor is None:
                    primary_failed_executor = str(executor_key)
                last_error = exec_result.get("error", "Bilinmeyen hata")
                last_source = f"{source}_error"

            return {
                "ok": False,
                "answer": None,
                "source": last_source,
                "error": last_error,
                "level": level,
                "router_decision": rd,
                "execution_decision": execution_decision,
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "data_class": data_class,
            }

        # --- fallback (clarify, no_answer, unknown) ---
        return {
            "ok": False,
            "answer": None,
            "source": decision or "unknown",
            "router_decision": rd,
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }
