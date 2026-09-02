"""AssistantExecutor quick reply tests."""
from __future__ import annotations


class _ExplodingRouter:
    def route(self, q):
        raise AssertionError(f"Quick reply should not call router: {q!r}")

class _ExplodingExecutor:
    def generate(self, *a, **kw):
        raise AssertionError("Quick reply should not call Ollama")


def test_merhaba_quick_reply():
    from agents.assistant_executor import AssistantExecutor
    ex = AssistantExecutor(router=_ExplodingRouter(), executor=_ExplodingExecutor())
    r = ex.ask("merhaba")
    assert r["ok"] is True
    assert r["source"] == "quick_reply"
    assert r["answer"]


def test_selam_quick_reply():
    from agents.assistant_executor import AssistantExecutor
    ex = AssistantExecutor(router=_ExplodingRouter(), executor=_ExplodingExecutor())
    r = ex.ask("selam")
    assert r["ok"] is True and r["source"] == "quick_reply"


def test_case_insensitive():
    from agents.assistant_executor import AssistantExecutor
    ex = AssistantExecutor(router=_ExplodingRouter(), executor=_ExplodingExecutor())
    r = ex.ask("MERHABA")
    assert r["source"] == "quick_reply"


def test_trailing_punct():
    from agents.assistant_executor import AssistantExecutor
    ex = AssistantExecutor(router=_ExplodingRouter(), executor=_ExplodingExecutor())
    r = ex.ask("merhaba!")
    assert r["source"] == "quick_reply"


def test_technical_question_not_quick_reply():
    from agents.assistant_executor import AssistantExecutor

    class FakeRouter:
        def route(self, q):
            return {"decision": "ask_external", "route": "external",
                    "confidence": 60, "reason": "test", "signals": {},
                    "cascade": {"level": "L2", "model": "m", "cost_tier": "cheap"}}

    class FakeExecutor:
        def generate(self, prompt, level="L2", **kw):
            return {"ok": True, "text": "cevap", "model": "m", "level": level, "latency_ms": 1}

    ex = AssistantExecutor(router=FakeRouter(), executor=FakeExecutor())
    r = ex.ask("Python listede tekrar eden elemanlari nasil buluruz?")
    assert r["source"] == "ollama"


def test_quick_reply_latency_ms_present():
    from agents.assistant_executor import AssistantExecutor
    ex = AssistantExecutor(router=_ExplodingRouter(), executor=_ExplodingExecutor())
    r = ex.ask("tamam")
    assert "latency_ms" in r
    assert r["latency_ms"] >= 0
