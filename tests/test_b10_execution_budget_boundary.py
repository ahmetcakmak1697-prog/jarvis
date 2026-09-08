"""B10: route without spending; consume API attempts at the executor boundary."""
from types import SimpleNamespace

import pytest

from b10_execution_support import pipeline


def test_local_answers_do_not_spend_or_require_external_budget(tmp_path, monkeypatch):
    executor, ledger, local, api = pipeline(tmp_path, monkeypatch)
    first = executor.ask("synthetic local question one")
    assert first["source"] == "ollama"
    assert ledger.stats()["today_count"] == 0
    ledger.check_and_consume("synthetic_prior_api")
    second = executor.ask("synthetic local question two")
    assert second["source"] == "ollama"
    assert len(local.calls) == 2
    assert api.calls == []
    assert ledger.stats()["today_count"] == 1


def test_cloud_attempt_consumes_once_and_exhaustion_falls_back_local(tmp_path, monkeypatch):
    executor, ledger, local, api = pipeline(tmp_path, monkeypatch, cloud=True)
    first = executor.ask("synthetic cloud question one")
    assert first["source"] == "api"
    assert ledger.stats()["today_count"] == 1
    second = executor.ask("synthetic cloud question two")
    assert second["source"] == "ollama"
    assert second["primary_failed_executor"] == "api"
    assert len(api.calls) == 1 and len(local.calls) == 1
    assert ledger.stats()["today_count"] == 1


@pytest.mark.parametrize("guard", ["redaction", "web_policy"])
def test_guard_failure_prevents_external_execution(tmp_path, monkeypatch, guard):
    def fail(*args, **kwargs):
        raise RuntimeError("SYNTHETIC_GUARD_FAILURE")
    policy = SimpleNamespace(decide=fail) if guard == "web_policy" else None
    executor, ledger, local, api = pipeline(tmp_path, monkeypatch, cloud=True, limit=5, web_policy=policy)
    if guard == "redaction":
        monkeypatch.setattr("agents.redaction_guard.RedactionGuard.sanitize_text", fail)
    result = executor.ask("synthetic unclassified question")
    assert result.get("blocked") is True
    assert result["router_decision"]["signals"]["guard_failed"] is True
    assert api.calls == [] and local.calls == []
    assert ledger.stats()["today_count"] == 0
    assert "SYNTHETIC_GUARD_FAILURE" not in result["answer"]
