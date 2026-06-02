"""C2.5 Telegram project intelligence command tests."""

from __future__ import annotations

from tools.telegram_agent import cmd_project_intel


def test_cmd_project_intel_output_shape():
    text = cmd_project_intel()

    assert "C2 Proje Zekasi" in text
    assert "Project: Jarvis v5" in text
    assert "Current phase: C2" in text
    assert "Last completed: C1" in text
    assert "Branch:" in text
    assert "Git clean:" in text
    assert "Roadmap confidence:" in text
    assert "Next phase:" in text
    assert "Recommended action:" in text
    assert "Reason:" in text
    assert "Acceptance criteria:" in text
    assert "Evidence:" in text
    assert "Komutlar:" in text


def test_cmd_project_intel_mentions_related_commands():
    text = cmd_project_intel()

    assert "/project_state" in text
    assert "/project" in text
    assert "/report" in text
    assert "/mem_status" in text


def test_cmd_project_intel_includes_acceptance_and_risk_context():
    text = cmd_project_intel()

    assert "Planner returns recommended_action" in text
    assert "Planner is deterministic" in text
    assert "Do not rely only on chat history" in text
