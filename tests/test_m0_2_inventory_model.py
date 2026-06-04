from agents.inventory_model import InventoryStore


def test_inventory_model_loads_default_files():
    store = InventoryStore()

    snapshot = store.load()

    assert snapshot.electronics["electronics"][0]["id"] == "arduino_01_kit"
    assert snapshot.safety_equipment["safety_equipment"][0]["id"] == "multimeter"


def test_inventory_model_validate_passes_for_default_files():
    store = InventoryStore()

    errors = store.validate()

    assert errors == []


def test_inventory_model_recommended_next_items():
    store = InventoryStore()

    items = store.recommended_next_items()

    ids = {item["id"] for item in items}

    assert "multimeter" in ids


def test_inventory_model_summary_contains_core_fields():
    store = InventoryStore()

    text = store.summary_text()

    assert "Inventory Model" in text
    assert "electronics: 2" in text
    assert "Recommended next:" in text


def test_inventory_model_validate_reports_invalid_status(tmp_path):
    inventory = tmp_path / "inventory"
    inventory.mkdir()

    (inventory / "tools.json").write_text(
        '{"schema_version":1,"tools":[{"id":"x","status":"bad"}]}',
        encoding="utf-8",
    )
    (inventory / "electronics.json").write_text(
        '{"schema_version":1,"electronics":[]}',
        encoding="utf-8",
    )
    (inventory / "materials.json").write_text(
        '{"schema_version":1,"materials":[]}',
        encoding="utf-8",
    )
    (inventory / "printer_supplies.json").write_text(
        '{"schema_version":1,"printer_supplies":[]}',
        encoding="utf-8",
    )
    (inventory / "safety_equipment.json").write_text(
        '{"schema_version":1,"safety_equipment":[]}',
        encoding="utf-8",
    )

    store = InventoryStore(root=tmp_path)

    errors = store.validate()

    assert "invalid_status:tools:x:bad" in errors
