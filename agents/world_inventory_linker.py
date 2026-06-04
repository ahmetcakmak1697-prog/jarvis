"""World + Inventory Linker - M0.3.

Connects M0 world model rooms with M0.2 inventory items.

Purpose:
- answer "which items are in which room?"
- detect inventory items pointing to unknown rooms
- provide a deterministic base for hobby room planning
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.inventory_model import InventoryStore
from agents.world_model import WorldModelStore


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RoomInventoryView:
    room_id: str
    room_name: str
    room_status: str
    devices: list[dict[str, Any]]
    inventory_items: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "room_status": self.room_status,
            "devices": self.devices,
            "inventory_items": self.inventory_items,
        }


class WorldInventoryLinker:
    """Build room-based views from world and inventory models."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.world = WorldModelStore(self.root)
        self.inventory = InventoryStore(self.root)

    def room_views(self) -> list[RoomInventoryView]:
        world_snapshot = self.world.load()
        inventory_snapshot = self.inventory.load()

        rooms = world_snapshot.rooms.get("rooms", [])
        devices = world_snapshot.devices.get("devices", [])

        inventory_items = self._all_inventory_items(inventory_snapshot.to_dict())

        views: list[RoomInventoryView] = []
        for room in rooms:
            room_id = str(room.get("id") or "")
            room_devices = [
                item for item in devices
                if item.get("room_id") == room_id
            ]
            room_inventory = [
                item for item in inventory_items
                if item.get("room_id") == room_id
            ]

            views.append(
                RoomInventoryView(
                    room_id=room_id,
                    room_name=str(room.get("name") or room_id or "unknown"),
                    room_status=str(room.get("status") or "unknown"),
                    devices=room_devices,
                    inventory_items=room_inventory,
                )
            )

        return views

    def hobby_room_items(self) -> dict[str, Any]:
        for view in self.room_views():
            if view.room_id == "hobby_room":
                return view.to_dict()
        return {
            "room_id": "hobby_room",
            "room_name": "hobby_room",
            "room_status": "missing",
            "devices": [],
            "inventory_items": [],
        }

    def validate_links(self) -> list[str]:
        errors: list[str] = []

        world_snapshot = self.world.load()
        inventory_snapshot = self.inventory.load()

        room_ids = {
            str(room.get("id"))
            for room in world_snapshot.rooms.get("rooms", [])
            if room.get("id")
        }

        for device in world_snapshot.devices.get("devices", []):
            room_id = device.get("room_id")
            if room_id and room_id not in room_ids:
                errors.append(f"unknown_room:device:{device.get('id', 'unknown')}:{room_id}")

        for item in self._all_inventory_items(inventory_snapshot.to_dict()):
            room_id = item.get("room_id")
            if room_id and room_id not in room_ids:
                errors.append(f"unknown_room:inventory:{item.get('id', 'unknown')}:{room_id}")

        return errors

    def summary_text(self) -> str:
        lines = [
            "World + Inventory",
            "",
        ]

        for view in self.room_views():
            lines.append(
                f"{view.room_name}: {len(view.devices)} devices, {len(view.inventory_items)} inventory items"
            )

        errors = self.validate_links()
        if errors:
            lines.extend(["", "Link errors:"])
            lines.extend(f"- {item}" for item in errors)

        return "\n".join(lines)

    def _all_inventory_items(self, inventory_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for section_key, section in inventory_data.items():
            collection = section.get(section_key, [])
            for item in collection:
                if isinstance(item, dict):
                    enriched = dict(item)
                    enriched["_inventory_section"] = section_key
                    items.append(enriched)

        return items
