"""Regression guard: Rich markup crash in _run_local_mode Ollama diagnostic.

Reproduces the bug where lines like "[yellow]...[/]" (stray closing tag)
or "[yellow]..." (unclosed tag) caused rich.errors.MarkupError at startup.
"""
from __future__ import annotations
import io
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from rich.errors import MarkupError


def _make_console() -> Console:
    return Console(file=io.StringIO(), highlight=False)


def test_ollama_diagnostic_strings_render_without_markup_error():
    """All four lines printed in the Ollama-unavailable branch must not raise MarkupError."""
    console = _make_console()
    strings = [
        "\n[red]❌ Ollama bağlanamadı![/red]",
        "[yellow]1. Ollama kurulu mu? → 1_windows_hazirlik.bat[/yellow]",
        "[yellow]2. Model var mı? → 2_model_indir.bat[/yellow]",
        "[yellow]3. 'ollama serve' çalışıyor mu?[/yellow]",
    ]
    for s in strings:
        try:
            console.print(s)
        except MarkupError as exc:
            pytest.fail(f"MarkupError on {s!r}: {exc}")


def test_run_local_mode_ollama_unavailable_does_not_crash(monkeypatch):
    """_run_local_mode() must return cleanly (no exception) when Ollama is down."""
    fake_agent = MagicMock()
    fake_agent.ollama_available = False

    with patch("agent.local_agent.LocalJarvisAgent", return_value=fake_agent):
        import main
        fake_console = _make_console()
        monkeypatch.setattr(main, "console", fake_console)
        main._run_local_mode()
