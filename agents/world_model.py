"""World Model - M0.

Minimal file-backed world model for Jarvis.

Purpose:
- load Ahmet's real-world context from JSON files
- keep personal environment separate from conversational memory
- provide deterministic access for future planning/reporting
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class WorldModelSnapshot:
    home: dict[str, Any]
    rooms: dict[str, Any]
    people: dict[str, Any]
    devices: dict[str, Any]
    modes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "home": self.home,
            "rooms": self.rooms,
            "people": self.people,
            "devices": self.devices,
            "modes": self.modes,
        }


class WorldModelStore:
    """Load and summarize Jarvis world model JSON files."""

    REQUIRED_FILES = {
        "home": "home.json",
        "rooms": "rooms.json",
        "people": "people.json",
        "devices": "devices.json",
        "modes": "modes.json",
    }

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.world_dir = self.root / "world"

    def load(self) -> WorldModelSnapshot:
        data = {}
        for key, filename in self.REQUIRED_FILES.items():
            data[key] = self._load_json(self.world_dir / filename)

        return WorldModelSnapshot(**data)

    def validate(self) -> list[str]:
        errors: list[str] = []

        for key, filename in self.REQUIRED_FILES.items():
            path = self.world_dir / filename
            if not path.exists():
                errors.append(f"missing:{filename}")
                continue

            try:
                data = self._load_json(path)
            except Exception:
                errors.append(f"invalid_json:{filename}")
                continue

            if not isinstance(data, dict):
                errors.append(f"root_not_object:{filename}")
                continue

            if "schema_version" not in data:
                errors.append(f"missing_schema_version:{filename}")

        return errors

    def summary_text(self) -> str:
        snapshot = self.load()

        rooms = snapshot.rooms.get("rooms", [])
        people = snapshot.people.get("people", [])
        devices = snapshot.devices.get("devices", [])
        modes = snapshot.modes.get("modes", [])

        lines = [
            "World Model",
            "",
            f"Home: {snapshot.home.get('name', 'unknown')}",
            f"Timezone: {snapshot.home.get('timezone', 'unknown')}",
            f"Primary user: {snapshot.home.get('primary_user', 'unknown')}",
            f"Rooms: {len(rooms)}",
            f"People: {len(people)}",
            f"Devices: {len(devices)}",
            f"Modes: {len(modes)}",
        ]

        if rooms:
            lines.extend(["", "Rooms:"])
            for room in rooms:
                lines.append(f"- {room.get('name', room.get('id', 'unknown'))}: {room.get('status', 'unknown')}")

        if devices:
            lines.extend(["", "Devices:"])
            for device in devices:
                lines.append(f"- {device.get('name', device.get('id', 'unknown'))}: {device.get('status', 'unknown')}")

        return "\n".join(lines)

    def _load_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be object: {path}")
        return data
