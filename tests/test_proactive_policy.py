"""Tests for ProactivePolicy - FAZ-3-E1."""

from typing import Any

import pytest

from agents.proactive_policy import ProactivePolicy, ProactiveDecision


def _policy(enabled: bool | None = None) -> ProactivePolicy:
    return ProactivePolicy(enabled=enabled)


def _state(priority: str = "normal", **kw: Any) -> dict[str, Any]:
    return {"priority": priority, **kw}


def _settings(**kw: Any) -> dict[str, Any]:
    return dict(kw)


# 1. Default flag absent -> suppress, requires opt-in
def test_default_flag_absent_suppress(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JARVIS_PROACTIVE_ENABLED", raising=False)
    policy = _policy()
    d = policy.decide(state=_state("normal"))
    assert d.decision == "suppress"
    assert d.reason == "proactive_disabled"
    assert d.requires_user_opt_in is True


# 2. JARVIS_PROACTIVE_ENABLED=0 -> suppress
def test_env_disabled_suppress(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JARVIS_PROACTIVE_ENABLED", "0")
    policy = _policy()
    d = policy.decide(state=_state("normal"))
    assert d.decision == "suppress"


# 3. Enabled values "1", "true", "yes", "on" -> can deliver high/critical
@pytest.mark.parametrize("val", ["1", "true", "yes", "on"])
def test_enabled_values_can_deliver_high(val: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JARVIS_PROACTIVE_ENABLED", val)
    policy = _policy()
    d = policy.decide(state=_state("high"))
    assert d.decision == "deliver"
    assert d.priority == "high"


@pytest.mark.parametrize("val", ["1", "true", "yes", "on"])
def test_enabled_values_can_deliver_critical(val: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JARVIS_PROACTIVE_ENABLED", val)
    policy = _policy()
    d = policy.decide(state=_state("critical"))
    assert d.decision == "deliver"


# 4. Muted user suppresses even if enabled
def test_muted_suppresses(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JARVIS_PROACTIVE_ENABLED", "1")
    policy = _policy()
    d = policy.decide(state=_state("high"), user_settings=_settings(muted=True))
    assert d.decision == "suppress"
    assert d.reason == "user_muted"


# 5. DND defers normal but allows critical
def test_dnd_defers_normal():
    policy = _policy(enabled=True)
    d = policy.decide(state=_state("normal"), user_settings=_settings(dnd=True))
    assert d.decision == "defer"
    assert d.reason == "dnd_active"


def test_dnd_allows_critical():
    policy = _policy(enabled=True)
    d = policy.decide(state=_state("critical"), user_settings=_settings(dnd=True))
    assert d.decision == "deliver"


# 6. Cooldown suppresses/defer repeated delivery
def test_cooldown_suppresses_low():
    policy = _policy(enabled=True)
    now = 1000.0
    d1 = policy.decide(state=_state("low"), now=now, last_delivery_at=None)
    assert d1.decision == "deliver"
    d2 = policy.decide(state=_state("low"), now=now + 10, last_delivery_at=now)
    assert d2.decision == "suppress"
    assert "cooldown" in d2.reason


def test_cooldown_expired_allows():
    policy = _policy(enabled=True)
    now = 1000.0
    d = policy.decide(state=_state("low"), now=now + 1000, last_delivery_at=now)
    assert d.decision == "deliver"


# 7. Low-priority night brief is not delivered (DND during night)
def test_low_priority_night_not_delivered():
    policy = _policy(enabled=True)
    d = policy.decide(state=_state("low"), user_settings=_settings(dnd=True))
    assert d.decision == "defer"


# 8. Critical security alert can deliver when enabled and not muted
def test_critical_security_alert_delivers():
    policy = _policy(enabled=True)
    d = policy.decide(state=_state("critical"), user_settings={})
    assert d.decision == "deliver"
    assert d.priority == "critical"


# 9. Policy never calls network/Telegram; use pure data only
def test_policy_pure_data():
    policy = _policy(enabled=True)
    d = policy.decide(state=_state("normal"))
    assert isinstance(d, ProactiveDecision)
    assert d.decision in ("deliver", "suppress", "defer")


# 10. Result schema includes all required fields
def test_result_schema():
    policy = _policy(enabled=True)
    d = policy.decide(state=_state("high"))
    as_dict = d.to_dict()
    for key in ("decision", "reason", "priority", "cooldown_seconds", "requires_user_opt_in"):
        assert key in as_dict, f"missing key: {key}"
    assert isinstance(as_dict["cooldown_seconds"], int)
    assert isinstance(as_dict["requires_user_opt_in"], bool)
