"""C2.1 Project state model tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from agents.project_state import ProjectStateStore


def test_default_state_contains_c2_transition_fields():
    with TemporaryDirectory() as td:
        store = ProjectStateStore(path=Path(td) / "project_state.json")
        state = store.default_state().to_dict()

        assert state["project"] == "Jarvis v5"
        assert state["current_phase"] == "C2"
        assert state["last_completed_phase"] == "C1"
        assert state["last_checkpoint"] == "docs/C1_MEMORY_CHECKPOINT.md"
        assert state["smoke_suite"] == "tests/run_smoke_suite.py"
        assert "C2.1 project state model" in state["next_steps"]
        assert state["risk_notes"]


def test_load_creates_state_file_when_missing():
    with TemporaryDirectory() as td:
        path = Path(td) / "project_state.json"
        store = ProjectStateStore(path=path)

        assert not path.exists()

        state = store.load()

        assert path.exists()
        assert state["project"] == "Jarvis v5"
        assert state["current_phase"] == "C2"


def test_save_updates_timestamp_and_preserves_fields():
    with TemporaryDirectory() as td:
        path = Path(td) / "project_state.json"
        store = ProjectStateStore(path=path)

        data = {
            "project": "Jarvis v5",
            "current_phase": "C2",
            "custom": "value",
        }

        saved = store.save(data)

        assert path.exists()
        assert saved["project"] == "Jarvis v5"
        assert saved["current_phase"] == "C2"
        assert saved["custom"] == "value"
        assert saved["updated_at"]

        loaded = store.load()
        assert loaded["custom"] == "value"


def test_refresh_returns_project_state_dict():
    with TemporaryDirectory() as td:
        path = Path(td) / "project_state.json"
        store = ProjectStateStore(path=path)

        state = store.refresh()

        assert state["project"] == "Jarvis v5"
        assert state["current_phase"] == "C2"
        assert state["last_completed_phase"] == "C1"
        assert isinstance(state["last_commits"], list)
        assert state["updated_at"]


def test_summary_contains_core_fields():
    with TemporaryDirectory() as td:
        path = Path(td) / "project_state.json"
        store = ProjectStateStore(path=path)
        store.refresh()

        summary = store.summary()

        assert "Project: Jarvis v5" in summary
        assert "Current phase: C2" in summary
        assert "Last completed: C1" in summary
        assert "Checkpoint: docs/C1_MEMORY_CHECKPOINT.md" in summary
        assert "Next steps:" in summary
