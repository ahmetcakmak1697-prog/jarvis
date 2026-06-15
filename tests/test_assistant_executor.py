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


class FakeExecutionPolicy:
    def __init__(self, decision):
        self._decision = decision
        self.calls = []

    def choose(self, router_decision):
        self.calls.append(router_decision)
        return self._decision


class FakeExecutorRegistry:
    def __init__(self, executors, order=None):
        self.executors = executors
        self.order = order
        self.get_calls = []
        self.order_calls = []

    def execution_order(self, decision):
        self.order_calls.append(decision)
        if self.order is not None:
            return list(self.order)
        return [decision.get("primary_executor")]

    def get(self, key):
        self.get_calls.append(key)
        return self.executors[key]


def test_assistant_executor_uses_execution_policy_and_registry_for_local_ollama():
    from agents.assistant_executor import AssistantExecutor

    fake_exec = FakeExecutor(text="Registry uzerinden cevap.")
    policy = FakeExecutionPolicy({
        "level": "L2",
        "destination": "local",
        "primary_executor": "ollama",
        "fallback_executor": None,
        "requires_approval": False,
        "reason": "local_first_default",
    })
    registry = FakeExecutorRegistry({"ollama": fake_exec})
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L2", "model": "m", "cost_tier": "cheap"},
        "signals": {},
    })

    ex = AssistantExecutor(router=router, execution_policy=policy, executor_registry=registry)
    result = ex.ask("Soru?")

    assert result["ok"] is True
    assert result["answer"] == "Registry uzerinden cevap."
    assert result["source"] == "ollama"
    assert result["level"] == "L2"
    assert result["execution_decision"]["destination"] == "local"
    assert registry.get_calls == ["ollama"]
    assert len(policy.calls) == 1


def test_assistant_executor_falls_back_to_ollama_when_primary_api_fails():
    from agents.assistant_executor import AssistantExecutor

    api_exec = FakeExecutor(ok=False)
    ollama_exec = FakeExecutor(text="Yerel fallback cevabi.")
    policy = FakeExecutionPolicy({
        "level": "L3",
        "destination": "cloud_api",
        "primary_executor": "api",
        "fallback_executor": "ollama",
        "requires_approval": False,
        "reason": "cloud_api_enabled_for_level",
    })
    registry = FakeExecutorRegistry(
        {"api": api_exec, "ollama": ollama_exec},
        order=["api", "ollama"],
    )
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L3", "model": "m", "cost_tier": "moderate"},
        "signals": {},
    })

    ex = AssistantExecutor(router=router, execution_policy=policy, executor_registry=registry)
    result = ex.ask("Zor soru?")

    assert result["ok"] is True
    assert result["answer"] == "Yerel fallback cevabi."
    assert result["source"] == "ollama"
    assert result["level"] == "L3"
    assert result["primary_failed_executor"] == "api"
    assert registry.get_calls == ["api", "ollama"]


class MissingPrimaryRegistry:
    def __init__(self, fallback_executor):
        self.fallback_executor = fallback_executor
        self.get_calls = []
        self.order_calls = []

    def execution_order(self, decision):
        self.order_calls.append(decision)
        return ["api", "ollama"]

    def get(self, key):
        self.get_calls.append(key)
        if key == "api":
            raise KeyError("api")
        if key == "ollama":
            return self.fallback_executor
        raise KeyError(key)


def test_assistant_executor_with_real_policy_can_route_l3_to_api():
    from agents.assistant_executor import AssistantExecutor
    from agents.execution_policy import ExecutionPolicy

    api_exec = FakeExecutor(text="Gercek policy API cevabi.")
    ollama_exec = FakeExecutor(text="Fallback.")
    registry = FakeExecutorRegistry(
        {"api": api_exec, "ollama": ollama_exec},
        order=["api", "ollama"],
    )
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L3", "model": "m", "cost_tier": "moderate"},
        "signals": {},
    })
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})

    ex = AssistantExecutor(router=router, execution_policy=policy, executor_registry=registry)
    result = ex.ask("Derin analiz yap.")

    assert result["ok"] is True
    assert result["answer"] == "Gercek policy API cevabi."
    assert result["source"] == "api"
    assert result["execution_decision"]["destination"] == "cloud_api"
    assert result["execution_decision"]["primary_executor"] == "api"
    assert result["execution_decision"]["fallback_executor"] == "ollama"
    assert registry.get_calls == ["api"]


def test_assistant_executor_falls_back_when_primary_executor_missing():
    from agents.assistant_executor import AssistantExecutor
    from agents.execution_policy import ExecutionPolicy

    ollama_exec = FakeExecutor(text="Primary yok, local fallback.")
    registry = MissingPrimaryRegistry(fallback_executor=ollama_exec)
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L3", "model": "m", "cost_tier": "moderate"},
        "signals": {},
    })
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})

    ex = AssistantExecutor(router=router, execution_policy=policy, executor_registry=registry)
    result = ex.ask("Derin analiz yap.")

    assert result["ok"] is True
    assert result["answer"] == "Primary yok, local fallback."
    assert result["source"] == "ollama"
    assert result["primary_failed_executor"] == "api"
    assert registry.get_calls == ["api", "ollama"]


def test_assistant_executor_real_policy_l4_premium_gate_skips_registry():
    from agents.assistant_executor import AssistantExecutor
    from agents.execution_policy import ExecutionPolicy

    registry = FakeExecutorRegistry({"api": FakeExecutor(), "ollama": FakeExecutor()})
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "premium_needed",
        "cascade": {"level": "L4", "model": "premium", "cost_tier": "expensive"},
        "signals": {},
    })
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3", "L4"})

    ex = AssistantExecutor(router=router, execution_policy=policy, executor_registry=registry)
    result = ex.ask("Premium seviye soru.")

    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["source"] == "premium_gate"
    assert result["execution_decision"]["requires_approval"] is True
    assert registry.get_calls == []
