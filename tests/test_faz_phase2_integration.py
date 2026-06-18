"""FAZ-PHASE2: Integration gate test — real policy + router + executor with fake researcher.

Tests the real wiring of WebResearchPolicy -> LocalFirstRouter -> AssistantExecutor
using a fake/stub WebResearcher so no live network is involved.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Local fake researcher (no network, no real WebResearcher import)
# ---------------------------------------------------------------------------
@dataclass
class FakeWebResearcher:
    report: str = "Fake web arastirma sonucu."
    raise_on_query: str | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def research(self, query: str, deep: bool = False) -> str:
        self.calls.append({"query": query, "deep": deep})
        if self._raise_on():
            msg = f"fake researcher crashed on: {query}"
            raise RuntimeError(msg)
        return self.report

    def _raise_on(self) -> bool:
        if self.raise_on_query is None:
            return False
        return any(self.raise_on_query in str(c) for c in self.calls)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_executor(web_research_enabled: bool = False):
    """Build a real-chain executor for integration tests."""
    # Do NOT import _build_assistant_executor here yet; tests import it directly.
    raise NotImplementedError("use the factory in each test")


# ===================================================================
# Test 1: default-off builder preserves no-live-web invariant
# ===================================================================
def test_default_off_builder_preserves_no_live_web():
    from tools.telegram_agent import _build_assistant_executor

    executor = _build_assistant_executor(web_research_enabled=False)

    assert executor._web_researcher is None
    assert executor._router._web_research_policy is None

    result = executor.ask("bugun Izmir hava durumu nasil?")

    assert result.get("source") != "web_research"


# ===================================================================
# Test 2: real policy + router + executor calls fake researcher
# ===================================================================
def test_real_policy_router_executor_calls_fake_researcher():
    from agents.web_research_policy import WebResearchPolicy
    from agents.local_first_router import LocalFirstRouter
    from agents.assistant_executor import AssistantExecutor
    from agents.cost_ledger import CostLedger

    policy = WebResearchPolicy()
    ledger = CostLedger(daily_limit=0)
    router = LocalFirstRouter(
        web_research_policy=policy,
        cost_ledger=ledger,
    )
    researcher = FakeWebResearcher(report="Izmir hava durumu: 28 derece, acik.")
    executor = AssistantExecutor(router=router, web_researcher=researcher)

    result = executor.ask("bugun Izmir hava durumu nasil?")

    assert result.get("ok") is True
    assert result.get("source") == "web_research"
    assert len(researcher.calls) == 1
    query = researcher.calls[0]["query"]
    assert "izmir" in query.lower() or "hava" in query.lower()
    assert researcher.calls[0]["deep"] is False


# ===================================================================
# Test 3: sensitive query blocked — fake researcher never called
# ===================================================================
def test_real_policy_sensitive_web_query_blocked_no_leak():
    from agents.web_research_policy import WebResearchPolicy
    from agents.local_first_router import LocalFirstRouter
    from agents.assistant_executor import AssistantExecutor
    from agents.cost_ledger import CostLedger

    policy = WebResearchPolicy()
    ledger = CostLedger(daily_limit=0)
    router = LocalFirstRouter(
        web_research_policy=policy,
        cost_ledger=ledger,
    )
    researcher = FakeWebResearcher(
        report="cagrilmamali",
        raise_on_query="TELEGRAM_BOT_TOKEN",
    )
    executor = AssistantExecutor(router=router, web_researcher=researcher)

    result = executor.ask("TELEGRAM_BOT_TOKEN nedir ve bunu web'de ara")

    src = result.get("source", "")
    assert src != "web_research"
    assert src in ("redacted_blocked", "web_research_blocked")
    assert len(researcher.calls) == 0
    answer = result.get("answer")
    if answer:
        assert "TELEGRAM_BOT_TOKEN" not in answer


# ===================================================================
# Test 4: non-web question does not become web_research accidentally
# ===================================================================
def test_external_api_path_still_works_with_policy_present_for_non_web_question():
    from agents.web_research_policy import WebResearchPolicy
    from agents.local_first_router import LocalFirstRouter
    from agents.assistant_executor import AssistantExecutor
    from agents.cost_ledger import CostLedger

    policy = WebResearchPolicy()
    ledger = CostLedger(daily_limit=0)
    router = LocalFirstRouter(
        web_research_policy=policy,
        cost_ledger=ledger,
    )
    researcher = FakeWebResearcher(report="cagrilmamali")
    executor = AssistantExecutor(router=router, web_researcher=researcher)

    result = executor.ask("Python'da set nedir?")

    assert result.get("source") not in ("web_research",)
    assert len(researcher.calls) == 0
