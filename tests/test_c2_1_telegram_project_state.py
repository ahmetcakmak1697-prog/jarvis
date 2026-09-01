"""C2.1 Telegram project state command tests."""

from __future__ import annotations

from tools.telegram_agent import cmd_project_state


def test_cmd_project_state_output_shape():
    text = cmd_project_state()

    assert "C2 Proje Durumu" in text
    assert "Project: Jarvis v5" in text
    assert "Current phase: C2" in text
    assert "Last completed: C1" in text
    assert "Status:" in text
    assert "Branch:" in text
    assert "Checkpoint: docs/C1_MEMORY_CHECKPOINT.md" in text
    assert "Next steps:" in text
    assert "Updated:" in text
    assert "Komutlar:" in text


def test_cmd_project_state_mentions_related_commands():
    text = cmd_project_state()

    assert "/project" in text
    assert "/report" in text
    assert "/mem_status" in text
