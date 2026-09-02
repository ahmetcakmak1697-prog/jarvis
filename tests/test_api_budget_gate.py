"""APIBudgetGate tests."""
from __future__ import annotations


class FakeLedger:
    def __init__(self, results=None, raise_exc=None):
        self.results = list(results or [])
        self.raise_exc = raise_exc
        self.calls = []

    def check_and_consume(self, call_type="external_call", dry_run=False):
        self.calls.append({"call_type": call_type, "dry_run": dry_run})
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.results:
            return self.results.pop(0)
        return {"allowed": True, "reason": "within_limit", "today_count": 1, "daily_limit": 50}


def test_api_budget_gate_allows_and_consumes():
    from agents.api_budget_gate import APIBudgetGate

    ledger = FakeLedger()
    gate = APIBudgetGate(ledger=ledger)

    result = gate.check_and_consume(provider="api", level="L3")

    assert result["allowed"] is True
    assert result["reason"] == "within_limit"
    assert result["provider"] == "api"
    assert result["level"] == "L3"
    assert ledger.calls == [{"call_type": "api_call", "dry_run": False}]


def test_api_budget_gate_denies_when_ledger_denies():
    from agents.api_budget_gate import APIBudgetGate

    ledger = FakeLedger(results=[
        {"allowed": False, "reason": "daily_limit_exceeded", "today_count": 50, "daily_limit": 50}
    ])
    gate = APIBudgetGate(ledger=ledger)

    result = gate.check_and_consume(provider="api", level="L3")

    assert result["allowed"] is False
    assert result["reason"] == "daily_limit_exceeded"


def test_api_budget_gate_fail_closed_on_ledger_exception():
    from agents.api_budget_gate import APIBudgetGate

    ledger = FakeLedger(raise_exc=RuntimeError("ledger broken"))
    gate = APIBudgetGate(ledger=ledger)

    result = gate.check_and_consume(provider="api", level="L3")

    assert result["allowed"] is False
    assert result["reason"] == "budget_gate_error"
    assert "ledger broken" in result["error"]
