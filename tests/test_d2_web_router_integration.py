"""D2: Web research router bridge integration tests.

Tests that LocalFirstRouter can classify web research queries
and AssistantExecutor handles the new routing decision safely.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from agents.local_first_router import LocalFirstRouter


@dataclass
class FakeWebResearchDecision:
    allow: bool
    mode: str
    reason: str
    sanitized_query: str = ""
    risk_flags: list[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FakeWebResearchPolicy:
    MODE_LOCAL_FILE = "local_file"
    MODE_LOCAL_CODE = "local_code"
    MODE_PROJECT_QA = "project_qa"
    MODE_GENERAL_QA = "general_qa"
    MODE_EXPLICIT_WEB = "explicit_web"
    MODE_CURRENT_INFO = "current_info"
    MODE_SENSITIVE_BLOCKED = "sensitive_blocked"

    def __init__(self, decision: FakeWebResearchDecision):
        self._decision = decision

    def decide(self, query: str, context: dict | None = None) -> FakeWebResearchDecision:
        return self._decision


class FakeQueryCache:
    def get_exact(self, question: str):
        return None


def test_web_research_explicit_current_triggers_web_decision():
    policy = FakeWebResearchPolicy(
        FakeWebResearchDecision(
            allow=True,
            mode="current_info",
            reason="Sorgu guncel bilgi gerektiriyor",
            sanitized_query="bugun izmir hava durumu",
        )
    )
    router = LocalFirstRouter(web_research_policy=policy, query_cache=FakeQueryCache())
    result = router.route("bugun Izmir hava durumu nedir")
    assert result["decision"] == "web_research"
    assert result["route"] == "web_research"
    assert result["signals"]["web_policy"]["mode"] == "current_info"
    assert result["sanitized_query"] == "bugun izmir hava durumu"
    assert result["confidence"] == 85


def test_web_research_explicit_web_triggers_web_decision():
    policy = FakeWebResearchPolicy(
        FakeWebResearchDecision(
            allow=True,
            mode="explicit_web",
            reason="Kullanici acikca web arastirmasi istedi",
            sanitized_query="internetten bak openai fiyatlar",
        )
    )
    router = LocalFirstRouter(web_research_policy=policy, query_cache=FakeQueryCache())
    result = router.route("internetten bak: OpenAI son model fiyatlar?")
    assert result["decision"] == "web_research"
    assert result["route"] == "web_research"
    assert result["signals"]["web_policy"]["mode"] == "explicit_web"


def test_web_policy_sensitive_blocked_does_not_call_external():
    """Sensitive query triggers redaction guard BEFORE web policy gate.

    The query 'TELEGRAM_BOT_TOKEN=123456' is caught by the redaction_guard
    which runs before the web research policy gate. This is correct D2
    behavior — redaction is the outer safety layer.
    """
    policy = FakeWebResearchPolicy(
        FakeWebResearchDecision(
            allow=False,
            mode="sensitive_blocked",
            reason="Sorgu hassas bilgi iceriyor",
            sanitized_query="TELEGRAM_BOT_TOKEN=[REDACTED]",
        )
    )
    router = LocalFirstRouter(web_research_policy=policy, query_cache=FakeQueryCache())
    result = router.route("TELEGRAM_BOT_TOKEN=123456 bunu kontrol et")
    # Redaction guard fires first -> redacted_blocked (not web_research_blocked)
    assert result["decision"] == "redacted_blocked"
    assert result["route"] == "redacted_blocked"
    assert result["confidence"] == 100


def test_web_policy_sensitive_blocked_non_secret_query():
    """A non-secret query blocked by web policy as sensitive."""
    policy = FakeWebResearchPolicy(
        FakeWebResearchDecision(
            allow=False,
            mode="sensitive_blocked",
            reason="Sorgu hassas bilgi iceriyor",
            sanitized_query="kisiye ozel bilgi",
        )
    )
    router = LocalFirstRouter(web_research_policy=policy, query_cache=FakeQueryCache(), redact_before_external=False)
    result = router.route("kisiye ozel bilgi arastir")
    assert result["decision"] == "web_research_blocked"
    assert result["route"] == "web_research_blocked"
    assert result["confidence"] == 100


def test_web_policy_deny_local_mode_falls_through_to_existing():
    """A general_qa denial should NOT produce web_research - it falls through."""
    policy = FakeWebResearchPolicy(
        FakeWebResearchDecision(
            allow=False,
            mode="general_qa",
            reason="Genel soru, web gerekmez",
            sanitized_query="merhaba nasilsin",
        )
    )
    router = LocalFirstRouter(web_research_policy=policy, query_cache=FakeQueryCache())
    result = router.route("Merhaba nasilsin?")
    assert result["decision"] != "web_research"
    # Should follow existing path (ask_external since no local knowledge)


def test_no_web_policy_preserves_existing_behavior():
    router_no_policy = LocalFirstRouter(query_cache=FakeQueryCache())
    result = router_no_policy.route("Merhaba nasilsin?")
    assert result["decision"] in ("ask_external", "clarify")


def test_policy_exception_fails_closed_to_existing_behavior():
    class RaisingPolicy:
        MODE_CURRENT_INFO = "current_info"
        MODE_EXPLICIT_WEB = "explicit_web"
        MODE_SENSITIVE_BLOCKED = "sensitive_blocked"

        def decide(self, query, context=None):
            raise RuntimeError("policy crashed")

    router = LocalFirstRouter(web_research_policy=RaisingPolicy(), query_cache=FakeQueryCache())
    result = router.route("Bugun hava nasil?")
    # Must not crash, must fall through to existing behavior
    assert result["decision"] in ("ask_external", "clarify")


def test_non_web_question_unchanged():
    policy = FakeWebResearchPolicy(
        FakeWebResearchDecision(
            allow=False,
            mode="general_qa",
            reason="Genel soru",
            sanitized_query="python set nedir",
        )
    )
    router = LocalFirstRouter(web_research_policy=policy, query_cache=FakeQueryCache())
    result = router.route("Python'da set nedir?")
    # general_qa denial with allow=False should not trigger web_research
    assert result["decision"] != "web_research"


# --- AssistantExecutor integration ---


from tests.test_assistant_executor import FakeRouter, FakeExecutor


def test_assistant_executor_web_research_decision_handled_safely():
    from agents.assistant_executor import AssistantExecutor

    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:current_info",
        "sanitized_query": "bugun izmir hava durumu",
        "signals": {"web_policy": {"mode": "current_info", "allow": True}},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("Bugun Izmir hava durumu nedir?")

    assert result["ok"] is True
    assert result["source"] == "web_research"
    assert "web arastirmasi" in result["answer"].lower()
    assert result["router_decision"]["decision"] == "web_research"


def test_assistant_executor_web_research_blocked_safely():
    from agents.assistant_executor import AssistantExecutor

    router = FakeRouter({
        "decision": "web_research_blocked",
        "route": "web_research_blocked",
        "confidence": 100,
        "reason": "web_policy_sensitive:hassas veri",
        "signals": {"web_policy": {"mode": "sensitive_blocked", "allow": False}},
    })
    ex = AssistantExecutor(router=router, executor=FakeExecutor())
    result = ex.ask("TELEGRAM_BOT_TOKEN=123456 bunu kontrol et")

    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["source"] == "web_research_blocked"
    assert "engellendi" in result["answer"].lower()


def test_assistant_executor_web_research_does_not_call_live_web():
    from agents.assistant_executor import AssistantExecutor

    dummy_exec = FakeExecutor(text="Live web cagrilmamali.")
    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:explicit_web",
        "sanitized_query": "internetten bak openai fiyatlar",
        "signals": {"web_policy": {"mode": "explicit_web", "allow": True}},
    })
    ex = AssistantExecutor(router=router, executor=dummy_exec)
    result = ex.ask("internetten bak: OpenAI fiyatlar?")

    assert result["ok"] is True
    assert result["source"] == "web_research"
    # dummy_exec should NOT have been called
    assert dummy_exec.calls == []


def test_normal_non_web_question_preserved():
    from agents.assistant_executor import AssistantExecutor

    dummy_exec = FakeExecutor(text="Normal cevap.")
    router = FakeRouter({
        "decision": "ask_external",
        "route": "external",
        "confidence": 60,
        "reason": "no_local_knowledge",
        "cascade": {"level": "L2", "model": "m", "cost_tier": "cheap"},
        "signals": {},
    })
    ex = AssistantExecutor(router=router, executor=dummy_exec)
    result = ex.ask("Python'da set nedir?")

    assert result["ok"] is True
    assert result["source"] == "ollama"
    assert len(dummy_exec.calls) == 1


# --- WebResearcher injection tests ---


class FakeWebResearcher:
    def __init__(self, report="Web arastirma sonucu.", raise_on=None):
        self._report = report
        self._raise_on = raise_on
        self.calls = []

    def research(self, query, deep=False):
        self.calls.append({"query": query, "deep": deep})
        if self._raise_on is not None and query == self._raise_on:
            raise RuntimeError("fake researcher crashed")
        return self._report


def test_web_research_no_researcher_uses_placeholder():
    from agents.assistant_executor import AssistantExecutor

    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:current_info",
        "sanitized_query": "bugun izmir hava durumu",
        "signals": {"web_policy": {"mode": "current_info", "allow": True}},
    })
    ex = AssistantExecutor(router=router)
    result = ex.ask("Bugun Izmir hava durumu nedir?")

    assert result["ok"] is True
    assert result["source"] == "web_research"
    assert "henuz bir web arastirmasi bileseni bagli degil" in result["answer"].lower()


def test_web_research_with_fake_researcher_called():
    from agents.assistant_executor import AssistantExecutor

    researcher = FakeWebResearcher(report="Izmir hava durumu: 30 derece, acik.")
    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:current_info",
        "sanitized_query": "bugun izmir hava durumu",
        "signals": {"web_policy": {"mode": "current_info", "allow": True}},
    })
    ex = AssistantExecutor(router=router, web_researcher=researcher)
    result = ex.ask("Bugun Izmir hava durumu nedir?")

    assert result["ok"] is True
    assert result["answer"] == "Izmir hava durumu: 30 derece, acik."
    assert result["source"] == "web_research"
    assert result["sanitized_query"] == "bugun izmir hava durumu"
    assert researcher.calls == [{"query": "bugun izmir hava durumu", "deep": False}]


def test_web_research_fake_researcher_exception_handled():
    from agents.assistant_executor import AssistantExecutor

    researcher = FakeWebResearcher(report="Hata olmamali.", raise_on="crash query")
    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:current_info",
        "sanitized_query": "crash query",
        "signals": {"web_policy": {"mode": "current_info", "allow": True}},
    })
    ex = AssistantExecutor(router=router, web_researcher=researcher)
    result = ex.ask("crash query")

    assert result["ok"] is False
    assert result["source"] == "web_research"
    assert "hata" in result["answer"].lower()


def test_web_research_does_not_call_injected_executor():
    from agents.assistant_executor import AssistantExecutor

    researcher = FakeWebResearcher(report="Sadece web sonucu.")
    dummy_exec = FakeExecutor(text="Burası cagrilmamali.")
    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:explicit_web",
        "sanitized_query": "internetten bak openai fiyatlar",
        "signals": {"web_policy": {"mode": "explicit_web", "allow": True}},
    })
    ex = AssistantExecutor(router=router, executor=dummy_exec, web_researcher=researcher)
    result = ex.ask("internetten bak: OpenAI fiyatlar?")

    assert result["ok"] is True
    assert result["source"] == "web_research"
    assert result["answer"] == "Sadece web sonucu."
    assert dummy_exec.calls == []


def test_web_research_fake_researcher_called_with_fallback_query():
    """When sanitized_query is missing, fall back to original question."""
    from agents.assistant_executor import AssistantExecutor

    researcher = FakeWebResearcher(report="Genel sonuc.")
    router = FakeRouter({
        "decision": "web_research",
        "route": "web_research",
        "confidence": 85,
        "reason": "web_policy_gate:explicit_web",
        "signals": {"web_policy": {"mode": "explicit_web", "allow": True}},
    })
    ex = AssistantExecutor(router=router, web_researcher=researcher)
    result = ex.ask("Orijinal soru metni")

    assert result["ok"] is True
    assert researcher.calls == [{"query": "Orijinal soru metni", "deep": False}]
