"""Project Workspace Model - M0.4.

Connects world projects with rooms, modes, devices, and inventory.

Purpose:
- answer "where does this project live?"
- identify missing project-linked equipment references
- provide deterministic project context for future briefings
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.inventory_model import InventoryStore
from agents.world_model import WorldModelStore


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ProjectWorkspaceView:
    project_id: str
    project_name: str
    status: str
    room_id: str
    room_name: str
    mode_id: str
    mode_name: str
    related_devices: list[dict[str, Any]]
    related_inventory: list[dict[str, Any]]
    next_focus: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "status": self.status,
            "room_id": self.room_id,
            "room_name": self.room_name,
            "mode_id": self.mode_id,
            "mode_name": self.mode_name,
            "related_devices": self.related_devices,
            "related_inventory": self.related_inventory,
            "next_focus": self.next_focus,
        }


class ProjectWorkspaceStore:
    """Build project workspace views from world + inventory models."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.world = WorldModelStore(self.root)
        self.inventory = InventoryStore(self.root)

    def project_views(self) -> list[ProjectWorkspaceView]:
        world = self.world.load()
        inventory = self.inventory.load()

        rooms_by_id = {
            str(room.get("id")): room
            for room in world.rooms.get("rooms", [])
            if room.get("id")
        }

        modes_by_id = {
            str(mode.get("id")): mode
            for mode in world.modes.get("modes", [])
            if mode.get("id")
        }

        devices_by_id = {
            str(device.get("id")): device
            for device in world.devices.get("devices", [])
            if device.get("id")
        }

        inventory_by_id = {
            str(item.get("id")): item
            for item in self._all_inventory_items(inventory.to_dict())
            if item.get("id")
        }

        views: list[ProjectWorkspaceView] = []

        for project in world.projects.get("projects", []):
            room_id = str(project.get("room_id") or "")
            mode_id = str(project.get("mode_id") or "")

            room = rooms_by_id.get(room_id, {})
            mode = modes_by_id.get(mode_id, {})

            related_devices = [
                devices_by_id[item_id]
                for item_id in project.get("related_devices", [])
                if item_id in devices_by_id
            ]

            related_inventory = [
                inventory_by_id[item_id]
                for item_id in project.get("related_inventory", [])
                if item_id in inventory_by_id
            ]

            views.append(
                ProjectWorkspaceView(
                    project_id=str(project.get("id") or ""),
                    project_name=str(project.get("name") or project.get("id") or "unknown"),
                    status=str(project.get("status") or "unknown"),
                    room_id=room_id,
                    room_name=str(room.get("name") or room_id or "unknown"),
                    mode_id=mode_id,
                    mode_name=str(mode.get("name") or mode_id or "unknown"),
                    related_devices=related_devices,
                    related_inventory=related_inventory,
                    next_focus=str(project.get("next_focus") or ""),
                )
            )

        return views

    def get_project(self, project_id: str) -> dict[str, Any]:
        for view in self.project_views():
            if view.project_id == project_id:
                return view.to_dict()
        return {}

    def validate_links(self) -> list[str]:
        world = self.world.load()
        inventory = self.inventory.load()

        room_ids = {
            str(room.get("id"))
            for room in world.rooms.get("rooms", [])
            if room.get("id")
        }
        mode_ids = {
            str(mode.get("id"))
            for mode in world.modes.get("modes", [])
            if mode.get("id")
        }
        device_ids = {
            str(device.get("id"))
            for device in world.devices.get("devices", [])
            if device.get("id")
        }
        inventory_ids = {
            str(item.get("id"))
            for item in self._all_inventory_items(inventory.to_dict())
            if item.get("id")
        }

        errors: list[str] = []

        for project in world.projects.get("projects", []):
            project_id = project.get("id") or "unknown"

            if project.get("room_id") not in room_ids:
                errors.append(f"unknown_room:project:{project_id}:{project.get('room_id')}")

            if project.get("mode_id") not in mode_ids:
                errors.append(f"unknown_mode:project:{project_id}:{project.get('mode_id')}")

            for device_id in project.get("related_devices", []):
                if device_id not in device_ids:
                    errors.append(f"unknown_device:project:{project_id}:{device_id}")

            for item_id in project.get("related_inventory", []):
                if item_id not in inventory_ids:
                    errors.append(f"unknown_inventory:project:{project_id}:{item_id}")

        return errors

    def summary_text(self) -> str:
        lines = [
            "Project Workspaces",
            "",
        ]

        for view in self.project_views():
            lines.append(
                f"{view.project_name}: room={view.room_name}, mode={view.mode_name}, "
                f"devices={len(view.related_devices)}, inventory={len(view.related_inventory)}"
            )

        errors = self.validate_links()
        if errors:
            lines.extend(["", "Link errors:"])
            lines.extend(f"- {item}" for item in errors)

        return "\n".join(lines)

    def _all_inventory_items(self, inventory_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for section_key, section in inventory_data.items():
            for item in section.get(section_key, []):
                if isinstance(item, dict):
                    enriched = dict(item)
                    enriched["_inventory_section"] = section_key
                    items.append(enriched)

        return items
