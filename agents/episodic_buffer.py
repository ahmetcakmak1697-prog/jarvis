"""C1.7 - EpisodicBuffer.

Append-only JSONL buffer for session/day context events.
Keeps recent activity visible without polluting long-term memory.

Scope (negative):
- No VectorMemory writes
- No LLM calls
- No Telegram commands
- No automatic promotion to core/recall/archival
- Pure JSONL append + prune
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_FILENAME = "episodic_buffer.jsonl"


class EpisodicBuffer:
    """Lightweight append-only buffer for episodic session events."""

    def __init__(self, root: Path | str | None = None) -> None:
        if root is None:
            root = Path(__file__).resolve().parents[1]
        self._memory_dir = Path(root) / "memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._memory_dir / DEFAULT_FILENAME

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        events = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
        return events

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_event(
        self,
        event_type: str,
        summary: str,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append a new event. Returns {ok, event} or {ok, reason}."""
        summary = str(summary or "").strip()
        if not summary:
            return {"ok": False, "reason": "blank_summary"}

        event: dict[str, Any] = {
            "id": f"ep_{uuid.uuid4().hex[:10]}",
            "event_type": str(event_type or "note").strip(),
            "summary": summary,
            "tags": [str(t) for t in (tags or []) if t],
            "meta": meta or {},
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        return {"ok": True, "event": event}

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return most recent events, newest first."""
        events = self._load()
        return list(reversed(events))[:max(1, int(limit))]

    def prune(self, max_items: int = 100) -> dict[str, Any]:
        """Keep only the most recent max_items events. Rewrites JSONL."""
        events = self._load()
        if len(events) <= max_items:
            return {"ok": True, "kept": len(events), "removed": 0}

        keep = events[-max_items:]
        with self._path.open("w", encoding="utf-8") as f:
            for ev in keep:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")

        return {"ok": True, "kept": len(keep), "removed": len(events) - len(keep)}

    def stats(self) -> dict[str, Any]:
        """Return total count and breakdown by event_type."""
        events = self._load()
        by_type: dict[str, int] = {}
        for ev in events:
            t = str(ev.get("event_type") or "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"total": len(events), "by_type": by_type}
