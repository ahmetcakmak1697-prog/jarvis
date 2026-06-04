from agents.world_inventory_linker import WorldInventoryLinker


def test_linker_builds_hobby_room_view():
    linker = WorldInventoryLinker()

    view = linker.hobby_room_items()

    assert view["room_id"] == "hobby_room"
    assert len(view["inventory_items"]) >= 2

    ids = {item["id"] for item in view["inventory_items"]}

    assert "arduino_01_kit" in ids
    assert "esp32_devkit" in ids


def test_linker_room_views_include_work_area_device():
    linker = WorldInventoryLinker()

    views = linker.room_views()

    work = [view for view in views if view.room_id == "work_area"][0]

    device_ids = {item["id"] for item in work.devices}

    assert "jarvis_pc" in device_ids


def test_linker_validate_links_passes_for_default_files():
    linker = WorldInventoryLinker()

    errors = linker.validate_links()

    assert errors == []


def test_linker_summary_contains_room_counts():
    linker = WorldInventoryLinker()

    text = linker.summary_text()

    assert "World + Inventory" in text
    assert "devices" in text
    assert "inventory items" in text
