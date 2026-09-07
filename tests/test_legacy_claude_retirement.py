"""B08: the retired direct Claude entry must never be selected again."""
from pathlib import Path
import io

import pytest
from rich.console import Console


@pytest.mark.parametrize("api_key", ["", "SYNTHETIC_TEST_VALUE"])
def test_auto_mode_stays_local_with_or_without_api_key(monkeypatch, api_key):
    import main

    monkeypatch.setattr("dotenv.load_dotenv", lambda: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    monkeypatch.setenv("USE_LOCAL_MODEL", "false")
    calls = []
    monkeypatch.setattr(main, "_run_local_mode", lambda: calls.append("local"))
    monkeypatch.setattr(main, "_run_claude_mode", lambda: calls.append("legacy"), raising=False)
    main.chat_loop()
    assert calls == ["local"]


def test_explicit_claude_mode_reports_retirement_without_starting_agent(monkeypatch):
    import main

    calls = []
    output = io.StringIO()
    monkeypatch.setattr(main, "console", Console(file=output, color_system=None))
    monkeypatch.setattr(main, "_run_claude_mode", lambda: calls.append("legacy"), raising=False)
    monkeypatch.setattr(main, "_run_local_mode", lambda: calls.append("local"))
    with pytest.raises(SystemExit) as exc:
        main.chat_loop("claude")
    assert exc.value.code == 2
    assert not calls
    assert "emekli" in output.getvalue().lower()


def test_retired_module_is_absent_and_supported_api_executors_remain():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "agent" / "jarvis_agent.py").exists()
    from agents.assistant_executor import AssistantExecutor
    from agents.api_executor import APIExecutor

    assert callable(AssistantExecutor.ask)
    assert callable(APIExecutor.generate)
