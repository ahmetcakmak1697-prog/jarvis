from agents.project_workspace import ProjectWorkspaceStore


def test_project_workspace_returns_jarvis_project():
    store = ProjectWorkspaceStore()

    project = store.get_project("jarvis_v5")

    assert project["project_id"] == "jarvis_v5"
    assert project["room_id"] == "work_area"
    assert project["mode_id"] == "development_mode"
    assert project["related_devices"][0]["id"] == "jarvis_pc"


def test_project_workspace_returns_arduino_project_inventory():
    store = ProjectWorkspaceStore()

    project = store.get_project("arduino_learning_path")

    inventory_ids = {item["id"] for item in project["related_inventory"]}

    assert "arduino_01_kit" in inventory_ids
    assert "multimeter" in inventory_ids


def test_project_workspace_validate_links_passes_for_default_files():
    store = ProjectWorkspaceStore()

    errors = store.validate_links()

    assert errors == []


def test_project_workspace_summary_contains_core_projects():
    store = ProjectWorkspaceStore()

    text = store.summary_text()

    assert "Project Workspaces" in text
    assert "Jarvis v5" in text
    assert "Arduino Learning Path" in text
