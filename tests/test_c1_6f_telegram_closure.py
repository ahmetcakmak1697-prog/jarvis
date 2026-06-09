"""C1.6F Telegram /day_closure command tests."""

from __future__ import annotations


def test_day_closure_returns_string():
    from tools.telegram_agent import cmd_day_closure
    result = cmd_day_closure()
    assert isinstance(result, str)
    assert len(result) > 0


def test_day_closure_telegram_safe():
    from tools.telegram_agent import cmd_day_closure
    result = cmd_day_closure()
    assert len(result) <= 3900


def test_day_closure_with_fake_candidates(monkeypatch):
    import agents.session_closure as sc_mod

    class FakeClosure:
        def __init__(self, **kwargs):
            pass
        def summarize(self):
            return "Bugunki hafiza ozeti efendim.\nSentez: 1 tema (jarvis)\nOnaylanan: 2 aday"

    monkeypatch.setattr(sc_mod, "SessionClosure", FakeClosure)

    from tools.telegram_agent import cmd_day_closure
    result = cmd_day_closure()
    assert "hafiza" in result.lower() or "jarvis" in result.lower()
