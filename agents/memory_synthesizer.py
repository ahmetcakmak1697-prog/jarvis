"""Memory Synthesizer - C1.6A.

State management skeleton for episodic -> semantic synthesis pipeline.

Scope (C1.6A):
- SynthesisState dataclass with load/save/default
- processed delete_id tracking (duplicate guard)
- broken JSON safe fallback

Not in scope (C1.6B+):
- LLM synthesis
- VectorMemory write
- ApprovalQueue integration
- Automatic permanent memory
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "c1.6"


@dataclass
class SynthesisState:
    schema_version: str = SCHEMA_VERSION
    last_run: str = ""
    processed_delete_ids: list[str] = field(default_factory=list)
    generated_count: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def mark_processed(self, delete_id: str) -> None:
        if delete_id and delete_id not in self.processed_delete_ids:
            self.processed_delete_ids.append(delete_id)

    def is_processed(self, delete_id: str) -> bool:
        return delete_id in self.processed_delete_ids


class MemorySynthesizerStore:
    """Load and persist SynthesisState."""

    DEFAULT_PATH = ROOT / "memory" / "synthesis_state.json"

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else self.DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_or_default(self) -> SynthesisState:
        if not self.path.exists():
            return SynthesisState()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return SynthesisState()

            return SynthesisState(
                schema_version=str(data.get("schema_version") or SCHEMA_VERSION),
                last_run=str(data.get("last_run") or ""),
                processed_delete_ids=list(data.get("processed_delete_ids") or []),
                generated_count=int(data.get("generated_count") or 0),
                updated_at=str(data.get("updated_at") or ""),
            )
        except Exception:
            return SynthesisState()

    def save(self, state: SynthesisState) -> None:
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        self.path.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def mark_processed(self, delete_id: str) -> SynthesisState:
        state = self.load_or_default()
        state.mark_processed(delete_id)
        self.save(state)
        return state

    def is_processed(self, delete_id: str) -> bool:
        return self.load_or_default().is_processed(delete_id)
