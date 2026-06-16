"""Tests for the data_class/privacy_level wiring added in FAZ 1B.13F.

Kept in a SEPARATE file from tests/test_assistant_executor.py on purpose:
that file is the existing, owner-maintained regression suite and is left
byte-for-byte untouched. These tests only exercise the new behaviour.
"""
from __future__ import annotations

from agents.assistant_executor import AssistantExecutor
from agents.execution_policy import ExecutionPolicy


class FakeRouter:
    def __init__(self, decision):
        self._decision = decision

    def route(self, question):
        return self._decision


class CapturingExecutor:
    """Records every kwarg it was called with, for kwarg-shape assertions."""

    def __init__(self, text="cevap", ok=True):
        self._text = text
        self._ok = ok
        self.calls: list[dict] = []

    def generate(self, prompt, level="L2", **kw):
        call = {"prompt": prompt, "level": level, **kw}
        self.calls.append(call)
        if not self._ok:
            return {"ok": False, "text": None, "model": "m", "level": level, "latency_ms": 0, "error": "fail"}
        return {"ok": True, "text": self._text, "model": "m", "level": level, "latency_ms": 10}


class StrictOllamaLikeExecutor:
    """Mirrors the REAL OllamaExecutor.generate signature exactly: it does
    NOT accept a privacy_level kwarg. If AssistantExecutor ever passes one
    by mistake, this raises TypeError, exactly like the real class would.
    """

    def __init__(self, text="ollama cevap"):
        self._text = text
        self.calls: list[dict] = []

    def generate(self, prompt, level="L2", model=None, dry_run=False, system_prompt=None):
        self.calls.append({"prompt": prompt, "level": level})
        return {"ok": True, "text": self._text, "model": "mistral-nemo", "level": level, "latency_ms": 10}


class FakeExecutorRegistry:
    def __init__(self, executors, order=None):
        self.executors = executors
        self.order = order
        self.get_calls = []

    def execution_order(self, decision):
        if self.order is not None:
            return list(self.order)
        return [decision.get("primary_executor")]

    def get(self, key):
        self.get_calls.append(key)
        return self.executors[key]


def _ask_external_router(question_level="L3"):
    return FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": question_level, "model": "m", "cost_tier": "moderate"},
        "signals": {},
    })


class AllowingAPIBudgetGate:
    def check_and_consume(self, **kwargs):
        return {"allowed": True, "reason": "within_limit", **kwargs}


# --------------------------------------------------------------------------
# The core safety property: ollama NEVER receives privacy_level
# --------------------------------------------------------------------------


def test_ollama_executor_never_receives_privacy_level_kwarg():
    # Uses a stand-in with the REAL OllamaExecutor.generate signature
    # (no privacy_level param). If AssistantExecutor passed it uniformly,
    # this would raise TypeError and the test would fail with an error,
    # not just an assertion failure.
    ollama_like = StrictOllamaLikeExecutor()
    policy = ExecutionPolicy()  # cloud_api_enabled=False -> destination "local"
    registry = FakeExecutorRegistry({"ollama": ollama_like})
    ex = AssistantExecutor(
        router=_ask_external_router("L2"),
        execution_policy=policy,
        executor_registry=registry,
    )
    result = ex.ask("ESHOT rolanti raporu hakkinda soru")
    assert result["ok"] is True
    assert ollama_like.calls == [{"prompt": "ESHOT rolanti raporu hakkinda soru", "level": "L2"}]


# --------------------------------------------------------------------------
# The "api" path DOES receive privacy_level, correctly classified
# --------------------------------------------------------------------------


def test_api_executor_receives_privacy_level_for_public_question():
    api_exec = CapturingExecutor(text="public cevap")
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})
    registry = FakeExecutorRegistry({"api": api_exec, "ollama": CapturingExecutor()}, order=["api", "ollama"])
    ex = AssistantExecutor(
        router=_ask_external_router("L3"),
        execution_policy=policy,
        executor_registry=registry,
        api_budget_gate=AllowingAPIBudgetGate(),
    )
    result = ex.ask("Python'da liste nasil ters cevrilir?")
    assert result["ok"] is True
    assert result["source"] == "api"
    assert api_exec.calls[0]["privacy_level"] == "PUBLIC"
    assert result["data_class"] == "public"


def test_api_executor_receives_work_internal_for_eshot_question():
    api_exec = CapturingExecutor(text="kurumsal cevap")
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})
    registry = FakeExecutorRegistry({"api": api_exec, "ollama": CapturingExecutor()}, order=["api", "ollama"])
    ex = AssistantExecutor(
        router=_ask_external_router("L3"),
        execution_policy=policy,
        executor_registry=registry,
        api_budget_gate=AllowingAPIBudgetGate(),
    )
    result = ex.ask("ESHOT rolanti raporundaki anomaliyi analiz et")
    assert api_exec.calls[0]["privacy_level"] == "WORK_INTERNAL"
    assert result["data_class"] == "institution_internal"


# --------------------------------------------------------------------------
# End-to-end safety proof: a real APIExecutor-shaped fake rejects
# WORK_INTERNAL and the system falls back to ollama automatically, with
# NO new branching logic in AssistantExecutor itself.
# --------------------------------------------------------------------------


class PrivacyAwareFakeAPIExecutor:
    """Mirrors the REAL APIExecutor's privacy guard behaviour exactly:
    rejects any privacy_level not in its allowed set, ok=False, no crash.
    """

    ALLOWED = {"PUBLIC", "REDACTED_LOW_RISK", "PERSONAL_REDACTED", "TECHNICAL", "CODE"}

    def __init__(self):
        self.calls: list[dict] = []

    def generate(self, prompt, level="L3", privacy_level="PUBLIC", **kw):
        self.calls.append({"prompt": prompt, "level": level, "privacy_level": privacy_level})
        if privacy_level not in self.ALLOWED:
            return {
                "ok": False,
                "text": None,
                "model": None,
                "level": level,
                "latency_ms": 0,
                "error": f"privacy_level {privacy_level!r} is not allowed for provider",
            }
        return {"ok": True, "text": "api cevap", "model": "deepseek/deepseek-chat", "level": level, "latency_ms": 10}


def test_eshot_question_falls_back_to_ollama_via_existing_privacy_guard():
    api_exec = PrivacyAwareFakeAPIExecutor()
    ollama_exec = CapturingExecutor(text="yerel ESHOT cevabi")
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})
    registry = FakeExecutorRegistry({"api": api_exec, "ollama": ollama_exec}, order=["api", "ollama"])
    ex = AssistantExecutor(
        router=_ask_external_router("L3"),
        execution_policy=policy,
        executor_registry=registry,
        api_budget_gate=AllowingAPIBudgetGate(),
    )
    result = ex.ask("ESHOT rolanti raporundaki anomaliyi analiz et")

    assert result["ok"] is True
    assert result["source"] == "ollama"
    assert result["answer"] == "yerel ESHOT cevabi"
    assert result["primary_failed_executor"] == "api"
    assert api_exec.calls[0]["privacy_level"] == "WORK_INTERNAL"
    assert "privacy_level" not in {k for c in ollama_exec.calls for k in c}


# --------------------------------------------------------------------------
# data_class is attached to the final no-answer response too
# --------------------------------------------------------------------------


def test_data_class_present_when_all_executors_fail():
    api_exec = CapturingExecutor(ok=False)
    ollama_exec = CapturingExecutor(ok=False)
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})
    registry = FakeExecutorRegistry({"api": api_exec, "ollama": ollama_exec}, order=["api", "ollama"])
    ex = AssistantExecutor(
        router=_ask_external_router("L3"),
        execution_policy=policy,
        executor_registry=registry,
        api_budget_gate=AllowingAPIBudgetGate(),
    )
    result = ex.ask("Python'da liste nasil ters cevrilir?")
    assert result["ok"] is False
    assert result["data_class"] == "public"
