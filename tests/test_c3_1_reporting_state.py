
import json
from pathlib import Path

from agents.reporting_state import ReportingStateStore


def test_build_default_state():
    store = ReportingStateStore()
    state = store.build()

    assert state.project
    assert state.report_layer_phase == "C3"
    assert isinstance(state.available_report_types, list)
    assert len(state.available_report_types) > 0


def test_save_and_load_roundtrip(tmp_path):
    store = ReportingStateStore()

    state = store.build()

    target = tmp_path / "reporting_state.json"

    store.save(state, target)

    loaded = store.load(target)

    assert loaded.project == state.project
    assert loaded.current_phase == state.current_phase
    assert loaded.report_layer_phase == state.report_layer_phase


def test_load_or_build_with_broken_json(tmp_path):
    store = ReportingStateStore()

    target = tmp_path / "broken.json"
    target.write_text("{invalid json", encoding="utf-8")

    state = store.load_or_build(target)

    assert state.project
    assert state.report_layer_phase == "C3"


def test_load_with_missing_fields(tmp_path):
    store = ReportingStateStore()

    target = tmp_path / "partial.json"

    target.write_text(
        json.dumps(
            {
                "project": "Jarvis",
                "current_phase": "C3"
            }
        ),
        encoding="utf-8",
    )

    state = store.load(target)

    assert state.project == "Jarvis"
    assert state.current_phase == "C3"
    assert state.report_layer_phase == "C3"


def test_risks_is_list():
    store = ReportingStateStore()

    state = store.build()

    assert isinstance(state.risks, list)


def test_report_types_contains_checkpoint_summary():
    store = ReportingStateStore()

    state = store.build()

    assert "checkpoint_summary" in state.available_report_types
