"""Internal Trace - C4-mini.

Append-only JSONL trace logger for Jarvis internal operations.

Purpose:
- record report generation steps
- record guard/fallback events
- record future organ/tool call traces
- sanitize payloads before writing logs
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.redaction_guard import RedactionGuard


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class TraceEvent:
    timestamp: str
    event: str
    layer: str
    status: str
    message: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "layer": self.layer,
            "status": self.status,
            "message": self.message,
            "payload": self.payload,
        }


class InternalTraceLogger:
    """Small append-only JSONL logger for internal Jarvis traces."""

    def __init__(self, root: Path | str = ROOT, path: Path | str | None = None):
        self.root = Path(root)
        self.path = Path(path) if path is not None else self.root / "logs" / "internal_trace.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.redactor = RedactionGuard()

    def log(
        self,
        event: str,
        layer: str = "core",
        status: str = "info",
        message: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_payload = self.redactor.sanitize_dict(payload or {})
        safe_message = self.redactor.sanitize_text(message).text

        record = TraceEvent(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            event=str(event or "unknown"),
            layer=str(layer or "core"),
            status=str(status or "info"),
            message=safe_message,
            payload=safe_payload,
        ).to_dict()

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        lines = self.path.read_text(encoding="utf-8", errors="ignore").splitlines()
        out: list[dict[str, Any]] = []

        for line in lines[-limit:]:
            try:
                item = json.loads(line)
            except Exception:
                continue

            if isinstance(item, dict):
                out.append(item)

        return out

    def stats(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"path": str(self.path), "total": 0, "events": {}, "layers": {}, "statuses": {}}

        events: dict[str, int] = {}
        layers: dict[str, int] = {}
        statuses: dict[str, int] = {}
        total = 0

        for item in self.tail(100000):
            total += 1
            event = str(item.get("event") or "unknown")
            layer = str(item.get("layer") or "unknown")
            status = str(item.get("status") or "unknown")

            events[event] = events.get(event, 0) + 1
            layers[layer] = layers.get(layer, 0) + 1
            statuses[status] = statuses.get(status, 0) + 1

        return {
            "path": str(self.path),
            "total": total,
            "events": events,
            "layers": layers,
            "statuses": statuses,
        }


if __name__ == "__main__":
    t = InternalTraceLogger()
    t.log(
        event="trace_self_test",
        layer="C4",
        status="ok",
        message="Internal trace self test",
        payload={"ok": True},
    )
    print(t.stats())
    print(t.tail(3))
