"""Audit Logger - D1.11.

Append-only JSONL audit log for web research and memory actions.

Why:
- trace where a memory came from
- trace user decisions
- debug wrong/old/unsafe knowledge later
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.path = self.root / "memory" / "audit_log.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event: str,
        query: str = "",
        candidate_id: str | None = None,
        action: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = payload or {}

        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "query_hash": self._hash(query),
            "candidate_id": candidate_id,
            "action": action,
            "payload": payload,
        }

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        lines = self.path.read_text(encoding="utf-8", errors="ignore").splitlines()
        out = []

        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue

        return out

    def stats(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"path": str(self.path), "total": 0, "events": {}}

        counts: dict[str, int] = {}
        total = 0

        for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                item = json.loads(line)
            except Exception:
                continue
            total += 1
            event = str(item.get("event") or "unknown")
            counts[event] = counts.get(event, 0) + 1

        return {
            "path": str(self.path),
            "total": total,
            "events": counts,
        }

    def _hash(self, text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


if __name__ == "__main__":
    a = AuditLogger()
    a.log(
        event="audit_self_test",
        query="test query",
        action="test",
        payload={"ok": True},
    )
    print(a.stats())
    print(a.tail(3))
