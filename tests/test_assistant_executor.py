"""AssistantExecutor tests ? Router + OllamaExecutor zinciri."""
from __future__ import annotations


class FakeRouter:
    def __init__(self, decision):
        self._decision = decision

    def route(self, question):
        return self._decision


class FakeExecutor:
    def __init__(self, text="Ollama cevabi.", ok=True):
        self._text = text
        self._ok = ok
        self.calls = []

    def generate(self, prompt, level="L2", **kw):
        self.calls.append({"prompt": prompt, "level": level})
        if not self._ok:
            return {"ok": False, "text": None, "model": "m", "level": level, "latency_ms": 0, "error": "Ollama kapali"}
        return {"ok": True, "text": self._text, "model": "mistral-nemo", "level": level, "latency_ms": 500}


def test_kc_answer_returned_directly():
    from agents.assistant_executor import AssistantExecutor
    router = FakeRouter({
        "decision": "answer_local",
        "route": "knowledge_card",
        "confidence": 100,
        "answer": "220W TDP.",
        "reason": "kc_hit",
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("RTX 3070 kac watt?")
    assert result["ok"] is True
    assert result["answer"] == "220W TDP."
    assert result["source"] == "knowledge_card"


def test_cache_answer_returned_directly():
    from agents.assistant_executor import AssistantExecutor
    router = FakeRouter({
        "decision": "answer_local",
        "route": "cache",
        "confidence": 95,
        "answer": "Cache cevabi.",
        "reason": "cache_hit",
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("Soru?")
    assert result["ok"] is True
    assert result["source"] == "cache"
    assert result["answer"] == "Cache cevabi."


def test_external_calls_ollama():
    from agents.assistant_executor import AssistantExecutor
    fake_exec = FakeExecutor(text="Python'da set kullanilir.")
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L2", "model": "mistral-nemo", "cost_tier": "cheap"},
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=fake_exec)
    result = ex.ask("Python listede tekrar edenleri nasil buluruz?")
    assert result["ok"] is True
    assert result["answer"] == "Python'da set kullanilir."
    assert result["source"] == "ollama"
    assert result["level"] == "L2"
    assert len(fake_exec.calls) == 1


def test_redacted_blocked_safe_response():
    from agents.assistant_executor import AssistantExecutor
    router = FakeRouter({
        "decision": "redacted_blocked",
        "route": "redacted_blocked",
        "confidence": 100,
        "reason": "redaction_guard_detected_sensitive_data_before_external",
        "signals": {"sensitive_detected": True},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("OPENAI_API_KEY=sk-test gonder")
    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["source"] == "redacted_blocked"
    assert "answer" in result


def test_external_blocked_safe_response():
    from agents.assistant_executor import AssistantExecutor
    router = FakeRouter({
        "decision": "external_blocked",
        "route": "external_blocked",
        "confidence": 0,
        "reason": "budget_limit:daily_limit_exceeded",
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("bilinmeyen soru")
    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["source"] == "external_blocked"


def test_ollama_failure_handled():
    from agents.assistant_executor import AssistantExecutor
    fake_exec = FakeExecutor(ok=False)
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L2", "model": "m", "cost_tier": "cheap"},
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=fake_exec)
    result = ex.ask("Soru?")
    assert result["ok"] is False
    assert "error" in result
    assert result["source"] == "ollama_error"


def test_result_has_required_fields():
    from agents.assistant_executor import AssistantExecutor
    router = FakeRouter({
        "decision": "answer_local",
        "route": "knowledge_card",
        "confidence": 100,
        "answer": "Cevap.",
        "reason": "kc",
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("Soru?")
    for field in ["ok", "answer", "source", "router_decision", "latency_ms"]:
        assert field in result, f"{field} eksik"
