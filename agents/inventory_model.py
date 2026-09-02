"""Inventory Model - M0.2.

Minimal file-backed inventory model for Jarvis.

Purpose:
- load maker/workshop inventory JSON files
- keep tools/materials/electronics separate from world model
- support future project recommendations and missing equipment checks
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class InventorySnapshot:
    tools: dict[str, Any]
    electronics: dict[str, Any]
    materials: dict[str, Any]
    printer_supplies: dict[str, Any]
    safety_equipment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tools": self.tools,
            "electronics": self.electronics,
            "materials": self.materials,
            "printer_supplies": self.printer_supplies,
            "safety_equipment": self.safety_equipment,
        }


class InventoryStore:
    """Load and summarize Jarvis inventory JSON files."""

    REQUIRED_FILES = {
        "tools": "tools.json",
        "electronics": "electronics.json",
        "materials": "materials.json",
        "printer_supplies": "printer_supplies.json",
        "safety_equipment": "safety_equipment.json",
    }

    VALID_STATUSES = {
        "available",
        "planned_purchase",
        "future_purchase",
        "future_target",
        "recommended_next",
        "missing",
    }

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.inventory_dir = self.root / "inventory"

    def load(self) -> InventorySnapshot:
        data = {}
        for key, filename in self.REQUIRED_FILES.items():
            data[key] = self._load_json(self.inventory_dir / filename)

        return InventorySnapshot(**data)

    def validate(self) -> list[str]:
        errors: list[str] = []

        for key, filename in self.REQUIRED_FILES.items():
            path = self.inventory_dir / filename
            if not path.exists():
                errors.append(f"missing:{filename}")
                continue

            try:
                data = self._load_json(path)
            except Exception:
                errors.append(f"invalid_json:{filename}")
                continue

            if "schema_version" not in data:
                errors.append(f"missing_schema_version:{filename}")

            collection = data.get(key)
            if not isinstance(collection, list):
                errors.append(f"missing_collection:{key}")
                continue

            for item in collection:
                if not isinstance(item, dict):
                    errors.append(f"invalid_item:{key}")
                    continue

                item_id = item.get("id") or "unknown"
                status = item.get("status")
                if status not in self.VALID_STATUSES:
                    errors.append(f"invalid_status:{key}:{item_id}:{status}")

        return errors

    def summary_text(self) -> str:
        snapshot = self.load()
        data = snapshot.to_dict()

        lines = [
            "Inventory Model",
            "",
        ]

        for key, section in data.items():
            items = section.get(key, [])
            lines.append(f"{key}: {len(items)}")

        next_items = self.recommended_next_items()
        if next_items:
            lines.extend(["", "Recommended next:"])
            for item in next_items:
                lines.append(f"- {item.get('name', item.get('id', 'unknown'))}")

        return "\n".join(lines)

    def recommended_next_items(self) -> list[dict[str, Any]]:
        snapshot = self.load()
        out: list[dict[str, Any]] = []

        for section_key, section in snapshot.to_dict().items():
            for item in section.get(section_key, []):
                if item.get("status") == "recommended_next":
                    out.append(item)

        return out

    def _load_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be object: {path}")
        return data
