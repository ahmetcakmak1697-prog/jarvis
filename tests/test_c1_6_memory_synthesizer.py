"""C1.6A Memory Synthesizer state tests."""

from __future__ import annotations

from pathlib import Path

from agents.memory_synthesizer import MemorySynthesizerStore, SynthesisState, SCHEMA_VERSION


def test_synthesizer_returns_default_when_no_file(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")
    state = store.load_or_default()

    assert isinstance(state, SynthesisState)
    assert state.schema_version == SCHEMA_VERSION
    assert state.processed_delete_ids == []
    assert state.generated_count == 0
    assert state.last_run == ""


def test_synthesizer_save_and_load_roundtrip(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")
    state = store.load_or_default()
    state.last_run = "2026-06-04T12:00:00"
    state.generated_count = 3
    store.save(state)

    loaded = store.load_or_default()
    assert loaded.last_run == "2026-06-04T12:00:00"
    assert loaded.generated_count == 3
    assert loaded.updated_at != ""


def test_synthesizer_broken_json_falls_back_to_default(tmp_path):
    path = tmp_path / "synthesis_state.json"
    path.write_text("{ not valid json }", encoding="utf-8")

    store = MemorySynthesizerStore(path=path)
    state = store.load_or_default()

    assert isinstance(state, SynthesisState)
    assert state.processed_delete_ids == []


def test_synthesizer_duplicate_guard(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")

    store.mark_processed("md_abc123")
    store.mark_processed("md_abc123")
    store.mark_processed("md_def456")

    state = store.load_or_default()
    assert state.processed_delete_ids.count("md_abc123") == 1
    assert "md_def456" in state.processed_delete_ids
    assert len(state.processed_delete_ids) == 2


def test_synthesizer_is_processed_returns_correct(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")

    assert store.is_processed("md_xyz") is False
    store.mark_processed("md_xyz")
    assert store.is_processed("md_xyz") is True


def test_synthesizer_default_path_is_memory_dir():
    store = MemorySynthesizerStore()
    assert "memory" in str(store.path)
    assert "synthesis_state.json" in str(store.path)
