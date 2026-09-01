"""Y0-3 CostLedger tests."""
from __future__ import annotations


def test_ledger_allows_when_under_limit(tmp_path):
    from agents.cost_ledger import CostLedger
    ledger = CostLedger(daily_limit=10, data_root=tmp_path)
    result = ledger.check_and_consume("external_call")
    assert result["allowed"] is True


def test_ledger_blocks_when_over_limit(tmp_path):
    from agents.cost_ledger import CostLedger
    ledger = CostLedger(daily_limit=3, data_root=tmp_path)
    for _ in range(3):
        ledger.check_and_consume("external_call")
    result = ledger.check_and_consume("external_call")
    assert result["allowed"] is False
    assert result["reason"] == "daily_limit_exceeded"


def test_ledger_persists_count(tmp_path):
    from agents.cost_ledger import CostLedger
    ledger = CostLedger(daily_limit=10, data_root=tmp_path)
    ledger.check_and_consume("external_call")
    ledger.check_and_consume("external_call")
    ledger2 = CostLedger(daily_limit=10, data_root=tmp_path)
    stats = ledger2.stats()
    assert stats["today_count"] == 2


def test_ledger_returns_stats(tmp_path):
    from agents.cost_ledger import CostLedger
    ledger = CostLedger(daily_limit=5, data_root=tmp_path)
    ledger.check_and_consume("external_call")
    stats = ledger.stats()
    assert "today_count" in stats
    assert "daily_limit" in stats
    assert "remaining" in stats
    assert stats["remaining"] == 4


def test_dry_run_does_not_consume(tmp_path):
    from agents.cost_ledger import CostLedger
    ledger = CostLedger(daily_limit=5, data_root=tmp_path)
    result = ledger.check_and_consume("external_call", dry_run=True)
    assert result["allowed"] is True
    assert ledger.stats()["today_count"] == 0


def test_unlimited_always_allows(tmp_path):
    from agents.cost_ledger import CostLedger
    ledger = CostLedger(daily_limit=0, data_root=tmp_path)
    for _ in range(100):
        r = ledger.check_and_consume("external_call")
    assert r["allowed"] is True
