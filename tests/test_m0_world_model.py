from pathlib import Path

from agents.world_model import WorldModelStore


def test_world_model_loads_default_files():
    store = WorldModelStore()

    snapshot = store.load()

    assert snapshot.home["primary_user"] == "Ahmet"
    assert snapshot.rooms["rooms"][0]["id"] == "hobby_room"
    assert snapshot.devices["devices"][0]["id"] == "jarvis_pc"


def test_world_model_validate_passes_for_default_files():
    store = WorldModelStore()

    errors = store.validate()

    assert errors == []


def test_world_model_summary_contains_core_fields():
    store = WorldModelStore()

    text = store.summary_text()

    assert "World Model" in text
    assert "Ahmet Home" in text
    assert "hobby_room" in store.load().rooms["rooms"][0]["id"]
    assert "Jarvis PC" in text


def test_world_model_validate_reports_missing_file(tmp_path):
    world = tmp_path / "world"
    world.mkdir()

    for name in ["home.json", "rooms.json", "people.json", "devices.json"]:
        (world / name).write_text('{"schema_version": 1}', encoding="utf-8")

    store = WorldModelStore(root=tmp_path)

    errors = store.validate()

    assert "missing:modes.json" in errors
